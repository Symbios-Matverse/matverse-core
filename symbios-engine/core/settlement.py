from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256, sha3_256
import json
from typing import Any, Mapping, Sequence

from .valuechain import CaptalsSnapshot, MBit, RightsObject, ValidationError


def _nonempty(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")
    return value


def _finite_nonnegative(name: str, value: Any) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValidationError(f"{name} must be a finite non-negative Decimal")
    return value


def _sha256_json(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(raw.encode("utf-8")).hexdigest()


def _sha3_json(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha3_256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EconomicObservation:
    """Measured economic inputs. Missing risk/debt are not silently zeroed."""

    risk: Decimal
    debt: Decimal
    evidence_hash: str
    instrument_version: str

    def validate(self) -> None:
        _finite_nonnegative("risk", self.risk)
        _finite_nonnegative("debt", self.debt)
        _nonempty("evidence_hash", self.evidence_hash)
        _nonempty("instrument_version", self.instrument_version)

    @property
    def object_hash(self) -> str:
        self.validate()
        return _sha256_json({
            "risk": str(self.risk),
            "debt": str(self.debt),
            "evidence_hash": self.evidence_hash,
            "instrument_version": self.instrument_version,
        })


@dataclass(frozen=True)
class SettlementReceipt:
    m_bit_hash: str
    rights_hash: str
    snapshot_hash: str
    economic_observation_hash: str
    policy_version: str
    sequence: int
    previous_receipt_hash: str = "GENESIS"
    schema_version: str = "captals-settlement/v1"

    def validate(self) -> None:
        for name in (
            "m_bit_hash", "rights_hash", "snapshot_hash", "economic_observation_hash",
            "policy_version", "previous_receipt_hash", "schema_version",
        ):
            _nonempty(name, getattr(self, name))
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValidationError("sequence must be a positive integer")
        if self.sequence == 1 and self.previous_receipt_hash != "GENESIS":
            raise ValidationError("first settlement receipt must start at GENESIS")
        if self.sequence > 1 and self.previous_receipt_hash == "GENESIS":
            raise ValidationError("non-first settlement receipt requires previous hash")

    @property
    def receipt_hash(self) -> str:
        self.validate()
        return _sha256_json({
            "schema_version": self.schema_version,
            "m_bit_hash": self.m_bit_hash,
            "rights_hash": self.rights_hash,
            "snapshot_hash": self.snapshot_hash,
            "economic_observation_hash": self.economic_observation_hash,
            "policy_version": self.policy_version,
            "sequence": self.sequence,
            "previous_receipt_hash": self.previous_receipt_hash,
        })

    def as_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "m_bit_hash": self.m_bit_hash,
            "rights_hash": self.rights_hash,
            "snapshot_hash": self.snapshot_hash,
            "economic_observation_hash": self.economic_observation_hash,
            "policy_version": self.policy_version,
            "sequence": self.sequence,
            "previous_receipt_hash": self.previous_receipt_hash,
            "receipt_hash": self.receipt_hash,
        }


def build_settlement_receipt(
    *,
    m_bit: MBit,
    rights: RightsObject,
    snapshot: CaptalsSnapshot,
    economic_observation: EconomicObservation,
    policy_version: str,
    sequence: int,
    previous_receipt_hash: str = "GENESIS",
) -> SettlementReceipt:
    m_bit.validate()
    rights.validate()
    snapshot.validate()
    economic_observation.validate()
    if rights.m_bit is None or rights.m_bit.object_hash != m_bit.object_hash:
        raise ValidationError("settlement receipt requires rights bound to the same MBit")
    if snapshot.created_value != m_bit.value_score or snapshot.cost != m_bit.cost_computed:
        raise ValidationError("snapshot is not bound to MBit value/cost")
    if snapshot.risk != economic_observation.risk or snapshot.debt != economic_observation.debt:
        raise ValidationError("snapshot risk/debt do not match measured economic observation")
    receipt = SettlementReceipt(
        m_bit_hash=m_bit.object_hash,
        rights_hash=rights.object_hash,
        snapshot_hash=snapshot.object_hash,
        economic_observation_hash=economic_observation.object_hash,
        policy_version=_nonempty("policy_version", policy_version),
        sequence=sequence,
        previous_receipt_hash=previous_receipt_hash,
    )
    receipt.validate()
    return receipt


def verify_ledger_chain(events: Sequence[Mapping[str, Any]]) -> str:
    """Verify the ACOA-style hash chain fail-closed; never resets to GENESIS on error."""

    previous = "GENESIS"
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise ValidationError(f"ledger event {index} must be a mapping")
        required = {"ts", "event_type", "payload", "prev_hash", "hash"}
        if set(event) != required:
            raise ValidationError(f"ledger event {index} schema mismatch")
        if event["prev_hash"] != previous:
            raise ValidationError(f"ledger event {index} previous hash mismatch")
        body = {
            "ts": event["ts"],
            "event_type": event["event_type"],
            "payload": event["payload"],
            "prev_hash": event["prev_hash"],
        }
        computed = _sha3_json(body)
        if event["hash"] != computed:
            raise ValidationError(f"ledger event {index} hash mismatch")
        previous = computed
    return previous


def prepare_acoa_ledger_event(*, settlement: SettlementReceipt, ts: str, existing_events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Prepare, but do not persist, a verified ACOA-compatible ledger event."""

    settlement.validate()
    _nonempty("ts", ts)
    previous = verify_ledger_chain(existing_events)
    event = {
        "ts": ts,
        "event_type": "CAPTALS_SETTLEMENT",
        "payload": settlement.as_payload(),
        "prev_hash": previous,
    }
    event["hash"] = _sha3_json(event)
    return event
