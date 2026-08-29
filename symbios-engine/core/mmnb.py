from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from .settlement import EconomicObservation, SettlementReceipt, verify_ledger_chain
from .valuechain import MBit, MemBit, MemNanoBit, MNB, RightsObject, ValidationError


def _hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MMNBEnvelope:
    """Replayable evidence envelope for one governed value trajectory."""

    mnb_hash: str
    mem_nano_bit_hash: str
    mem_bit_hash: str
    m_bit_hash: str
    rights_hash: str
    economic_observation_hash: str
    settlement_receipt_hash: str
    ledger_tip_hash: str
    schema_version: str = "mmnb/value-trajectory/v1"

    @property
    def envelope_hash(self) -> str:
        self.validate()
        return _hash({
            "schema_version": self.schema_version,
            "mnb_hash": self.mnb_hash,
            "mem_nano_bit_hash": self.mem_nano_bit_hash,
            "mem_bit_hash": self.mem_bit_hash,
            "m_bit_hash": self.m_bit_hash,
            "rights_hash": self.rights_hash,
            "economic_observation_hash": self.economic_observation_hash,
            "settlement_receipt_hash": self.settlement_receipt_hash,
            "ledger_tip_hash": self.ledger_tip_hash,
        })

    def validate(self) -> None:
        for name, value in self.__dict__.items():
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{name} must be a non-empty string")


def build_mmnb_envelope(
    *,
    mnb: MNB,
    mem_nano_bit: MemNanoBit,
    mem_bit: MemBit,
    m_bit: MBit,
    rights: RightsObject,
    economic_observation: EconomicObservation,
    settlement: SettlementReceipt,
    ledger_events: Sequence[Mapping[str, Any]],
) -> MMNBEnvelope:
    """Verify the complete lineage and return an immutable replay commitment.

    This function does not infer missing links. Every layer must be supplied and
    must cryptographically/structurally bind to the adjacent layer.
    """

    mnb.validate()
    mem_nano_bit.validate()
    mem_bit.validate()
    m_bit.validate()
    rights.validate()
    economic_observation.validate()
    settlement.validate()

    if mem_nano_bit.mnb.object_hash != mnb.object_hash:
        raise ValidationError("MMNB lineage mismatch: MNB -> MemNanoBit")
    if mem_bit.mem_nano_bit.object_hash != mem_nano_bit.object_hash:
        raise ValidationError("MMNB lineage mismatch: MemNanoBit -> MemBit")
    if m_bit.mem_bit.object_hash != mem_bit.object_hash:
        raise ValidationError("MMNB lineage mismatch: MemBit -> MBit")
    if rights.mem_bit.object_hash != mem_bit.object_hash:
        raise ValidationError("MMNB lineage mismatch: MemBit -> Rights")
    if rights.m_bit is None or rights.m_bit.object_hash != m_bit.object_hash:
        raise ValidationError("MMNB lineage mismatch: MBit -> Rights")
    if settlement.m_bit_hash != m_bit.object_hash:
        raise ValidationError("MMNB lineage mismatch: MBit -> Settlement")
    if settlement.rights_hash != rights.object_hash:
        raise ValidationError("MMNB lineage mismatch: Rights -> Settlement")
    if settlement.economic_observation_hash != economic_observation.object_hash:
        raise ValidationError("MMNB lineage mismatch: EconomicObservation -> Settlement")

    ledger_tip = verify_ledger_chain(ledger_events)
    if ledger_tip == "GENESIS":
        raise ValidationError("MMNB requires a persisted settlement ledger event")

    matching = [
        event for event in ledger_events
        if event.get("event_type") == "CAPTALS_SETTLEMENT"
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("receipt_hash") == settlement.receipt_hash
    ]
    if len(matching) != 1:
        raise ValidationError("MMNB requires exactly one ledger event for the settlement receipt")

    envelope = MMNBEnvelope(
        mnb_hash=mnb.object_hash,
        mem_nano_bit_hash=mem_nano_bit.object_hash,
        mem_bit_hash=mem_bit.object_hash,
        m_bit_hash=m_bit.object_hash,
        rights_hash=rights.object_hash,
        economic_observation_hash=economic_observation.object_hash,
        settlement_receipt_hash=settlement.receipt_hash,
        ledger_tip_hash=ledger_tip,
    )
    envelope.validate()
    return envelope
