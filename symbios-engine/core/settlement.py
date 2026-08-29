from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256, sha3_256
import json
import re
from typing import Any, Mapping, Sequence

from .valuechain import CaptalsSnapshot, MBit, RightsObject, ValidationError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _nonempty(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")
    return value


def _sha256_hex(name: str, value: Any) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValidationError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _finite_nonnegative(name: str, value: Any) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValidationError(f"{name} must be a finite non-negative Decimal")
    return value


def _sha256_json(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(raw.encode("utf-8")).hexdigest()


def _acoa_hash(payload: Mapping[str, Any]) -> str:
    """Exact legacy ACOA event hash: json.dumps(sort_keys=True, ensure_ascii=False) + SHA3-256."""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return sha3_256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EconomicObservation:
    risk: Decimal
    debt: Decimal
    evidence_hash: str
    instrument_version: str

    def validate(self) -> None:
        _finite_nonnegative("risk", self.risk)
        _finite_nonnegative("debt", self.debt)
        _sha256_hex("evidence_hash", self.evidence_hash)
        _nonempty("instrument_version", self.instrument_version)

    @property
    def object_hash(self) -> str:
        self.validate()
        return _sha256_json({"risk": str(self.risk), "debt": str(self.debt), "evidence_hash": self.evidence_hash, "instrument_version": self.instrument_version})


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
        for name in ("m_bit_hash", "rights_hash", "snapshot_hash", "economic_observation_hash"):
            _sha256_hex(name, getattr(self, name))
        for name in ("policy_version", "schema_version"):
            _nonempty(name, getattr(self, name))
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValidationError("sequence must be a positive integer")
        if self.sequence == 1:
            if self.previous_receipt_hash != "GENESIS": raise ValidationError("first settlement receipt must start at GENESIS")
        else:
            _sha256_hex("previous_receipt_hash", self.previous_receipt_hash)

    @property
    def receipt_hash(self) -> str:
        self.validate()
        return _sha256_json({"schema_version": self.schema_version, "m_bit_hash": self.m_bit_hash, "rights_hash": self.rights_hash, "snapshot_hash": self.snapshot_hash, "economic_observation_hash": self.economic_observation_hash, "policy_version": self.policy_version, "sequence": self.sequence, "previous_receipt_hash": self.previous_receipt_hash})

    def as_payload(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "m_bit_hash": self.m_bit_hash, "rights_hash": self.rights_hash, "snapshot_hash": self.snapshot_hash, "economic_observation_hash": self.economic_observation_hash, "policy_version": self.policy_version, "sequence": self.sequence, "previous_receipt_hash": self.previous_receipt_hash, "receipt_hash": self.receipt_hash}


def build_settlement_receipt(*, m_bit: MBit, rights: RightsObject, snapshot: CaptalsSnapshot, economic_observation: EconomicObservation, policy_version: str, sequence: int, previous_receipt_hash: str = "GENESIS") -> SettlementReceipt:
    m_bit.validate(); rights.validate(); snapshot.validate(); economic_observation.validate()
    if rights.m_bit is None or rights.m_bit.object_hash != m_bit.object_hash: raise ValidationError("settlement receipt requires rights bound to the same MBit")
    if snapshot.created_value != m_bit.value_score or snapshot.cost != m_bit.cost_computed: raise ValidationError("snapshot is not bound to MBit value/cost")
    if snapshot.risk != economic_observation.risk or snapshot.debt != economic_observation.debt: raise ValidationError("snapshot risk/debt do not match measured economic observation")
    receipt = SettlementReceipt(m_bit.object_hash, rights.object_hash, snapshot.object_hash, economic_observation.object_hash, _nonempty("policy_version", policy_version), sequence, previous_receipt_hash)
    receipt.validate(); return receipt


def _validated_settlement_payload(payload: Any, index: int) -> SettlementReceipt:
    if not isinstance(payload, Mapping): raise ValidationError(f"ledger settlement {index} payload must be a mapping")
    required = {"schema_version","m_bit_hash","rights_hash","snapshot_hash","economic_observation_hash","policy_version","sequence","previous_receipt_hash","receipt_hash"}
    if set(payload) != required: raise ValidationError(f"ledger settlement {index} payload schema mismatch")
    receipt = SettlementReceipt(payload["m_bit_hash"], payload["rights_hash"], payload["snapshot_hash"], payload["economic_observation_hash"], payload["policy_version"], payload["sequence"], payload["previous_receipt_hash"], payload["schema_version"])
    receipt.validate()
    if payload["receipt_hash"] != receipt.receipt_hash: raise ValidationError(f"ledger settlement {index} receipt hash mismatch")
    return receipt


def verify_ledger_chain(events: Sequence[Mapping[str, Any]]) -> str:
    previous = "GENESIS"
    settlement_previous = "GENESIS"
    settlement_sequence = 0
    seen_receipts: set[str] = set()
    seen_mbits: set[str] = set()
    for index, event in enumerate(events):
        if not isinstance(event, Mapping): raise ValidationError(f"ledger event {index} must be a mapping")
        required = {"ts", "event_type", "payload", "prev_hash", "hash"}
        if set(event) != required: raise ValidationError(f"ledger event {index} schema mismatch")
        if event["prev_hash"] != previous: raise ValidationError(f"ledger event {index} previous hash mismatch")
        body = {"ts": event["ts"], "event_type": event["event_type"], "payload": event["payload"], "prev_hash": event["prev_hash"]}
        computed = _acoa_hash(body)
        if event["hash"] != computed: raise ValidationError(f"ledger event {index} hash mismatch")
        if event["event_type"] == "CAPTALS_SETTLEMENT":
            receipt = _validated_settlement_payload(event["payload"], index)
            if receipt.sequence != settlement_sequence + 1: raise ValidationError(f"ledger settlement {index} sequence mismatch")
            if receipt.previous_receipt_hash != settlement_previous: raise ValidationError(f"ledger settlement {index} previous receipt mismatch")
            if receipt.receipt_hash in seen_receipts: raise ValidationError(f"ledger settlement {index} duplicate receipt")
            if receipt.m_bit_hash in seen_mbits: raise ValidationError(f"ledger settlement {index} duplicate MBit settlement")
            settlement_sequence = receipt.sequence; settlement_previous = receipt.receipt_hash; seen_receipts.add(receipt.receipt_hash); seen_mbits.add(receipt.m_bit_hash)
        previous = computed
    return previous


def prepare_acoa_ledger_event(*, settlement: SettlementReceipt, ts: str | float, existing_events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Prepare, but do not persist, an event byte-compatible with legacy ACOA hashing."""
    settlement.validate()
    if isinstance(ts, bool) or not isinstance(ts, (str, int, float)) or (isinstance(ts, str) and not ts.strip()): raise ValidationError("ts must be a non-empty string or numeric ACOA timestamp")
    previous = verify_ledger_chain(existing_events)
    prior = [event for event in existing_events if event.get("event_type") == "CAPTALS_SETTLEMENT"]
    if not prior:
        if settlement.sequence != 1 or settlement.previous_receipt_hash != "GENESIS": raise ValidationError("first ledger settlement must be sequence 1 from GENESIS")
    else:
        last = _validated_settlement_payload(prior[-1]["payload"], len(existing_events)-1)
        if settlement.sequence != last.sequence + 1: raise ValidationError("settlement sequence does not continue ledger")
        if settlement.previous_receipt_hash != last.receipt_hash: raise ValidationError("settlement previous receipt does not match ledger")
        if any(event["payload"].get("m_bit_hash") == settlement.m_bit_hash for event in prior): raise ValidationError("MBit already settled")
    event = {"ts": ts, "event_type": "CAPTALS_SETTLEMENT", "payload": settlement.as_payload(), "prev_hash": previous}
    event["hash"] = _acoa_hash(event)
    return event
