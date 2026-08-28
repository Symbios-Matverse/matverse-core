from __future__ import annotations

from dataclasses import dataclass, field, asdict
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


class ValidationError(ValueError):
    pass


class Decision(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class RightKind(str, Enum):
    USE = "use"
    EXECUTE = "execute"
    INTEGRATE = "integrate"
    MODIFY = "modify"
    REDISTRIBUTE = "redistribute"
    SUBLICENSE = "sublicense"
    COMMERCIAL_USE = "commercial_use"


def _require_nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MNB:
    event_id: str
    source: str
    content_hash: str
    context_hash: str
    timestamp: str
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        for name in ("event_id", "source", "content_hash", "context_hash", "timestamp"):
            _require_nonempty(name, getattr(self, name))

    @property
    def object_hash(self) -> str:
        self.validate()
        return _canonical_hash(asdict(self))


@dataclass(frozen=True)
class MemNanoBit:
    mnb: MNB
    continuity_id: str
    relation_hashes: Sequence[str] = field(default_factory=tuple)

    def validate(self) -> None:
        self.mnb.validate()
        _require_nonempty("continuity_id", self.continuity_id)
        if any(not isinstance(x, str) or not x for x in self.relation_hashes):
            raise ValidationError("relation_hashes must contain non-empty strings")

    @property
    def object_hash(self) -> str:
        self.validate()
        return _canonical_hash({
            "mnb_hash": self.mnb.object_hash,
            "continuity_id": self.continuity_id,
            "relation_hashes": list(self.relation_hashes),
        })


@dataclass(frozen=True)
class MemBit:
    mem_nano_bit: MemNanoBit
    decision_gate: Decision
    evidence_hash: str
    policy_version: str
    signer_key_id: str
    authority_scope: str
    claim_type: str = "formal_commitment"

    def validate(self) -> None:
        self.mem_nano_bit.validate()
        if self.decision_gate not in (Decision.PASS, Decision.HOLD):
            raise ValidationError("MemBit can only be materialized from PASS or HOLD")
        for name in ("evidence_hash", "policy_version", "signer_key_id", "authority_scope", "claim_type"):
            _require_nonempty(name, getattr(self, name))

    @property
    def object_hash(self) -> str:
        self.validate()
        return _canonical_hash({
            "mem_nano_bit_hash": self.mem_nano_bit.object_hash,
            "decision_gate": self.decision_gate.value,
            "evidence_hash": self.evidence_hash,
            "policy_version": self.policy_version,
            "signer_key_id": self.signer_key_id,
            "authority_scope": self.authority_scope,
            "claim_type": self.claim_type,
        })


@dataclass(frozen=True)
class MBit:
    mem_bit: MemBit
    trail_id: str
    milestone_id: str
    value_score: Decimal
    impact_metrics: Mapping[str, Decimal]
    cost_computed: Decimal = Decimal("0")

    def validate(self) -> None:
        self.mem_bit.validate()
        if self.mem_bit.decision_gate != Decision.PASS:
            raise ValidationError("MBit requires a PASS MemBit")
        for name in ("trail_id", "milestone_id"):
            _require_nonempty(name, getattr(self, name))
        if self.value_score < 0 or self.cost_computed < 0:
            raise ValidationError("value_score and cost_computed must be non-negative")
        if any(v < 0 for v in self.impact_metrics.values()):
            raise ValidationError("impact metrics must be non-negative")

    @property
    def object_hash(self) -> str:
        self.validate()
        return _canonical_hash({
            "mem_bit_hash": self.mem_bit.object_hash,
            "trail_id": self.trail_id,
            "milestone_id": self.milestone_id,
            "value_score": str(self.value_score),
            "impact_metrics": {k: str(v) for k, v in sorted(self.impact_metrics.items())},
            "cost_computed": str(self.cost_computed),
        })


@dataclass(frozen=True)
class RightsObject:
    artifact_id: str
    mem_bit: MemBit
    rights: frozenset[RightKind]
    licensor: str
    licensee: str
    scope: Mapping[str, Any]
    economics: Mapping[str, Decimal] = field(default_factory=dict)
    m_bit: MBit | None = None

    def validate(self) -> None:
        self.mem_bit.validate()
        for name in ("artifact_id", "licensor", "licensee"):
            _require_nonempty(name, getattr(self, name))
        if not self.rights:
            raise ValidationError("at least one right is required")
        if self.m_bit is not None:
            self.m_bit.validate()
            if self.m_bit.mem_bit.object_hash != self.mem_bit.object_hash:
                raise ValidationError("m_bit must derive from the same mem_bit")
        if any(v < 0 for v in self.economics.values()):
            raise ValidationError("economics values must be non-negative")

    @property
    def object_hash(self) -> str:
        self.validate()
        return _canonical_hash({
            "artifact_id": self.artifact_id,
            "mem_bit_hash": self.mem_bit.object_hash,
            "m_bit_hash": None if self.m_bit is None else self.m_bit.object_hash,
            "rights": sorted(x.value for x in self.rights),
            "licensor": self.licensor,
            "licensee": self.licensee,
            "scope": self.scope,
            "economics": {k: str(v) for k, v in sorted(self.economics.items())},
        })


@dataclass(frozen=True)
class CaptalsSnapshot:
    created_value: Decimal
    captured_value: Decimal
    cost: Decimal
    risk: Decimal
    debt: Decimal
    accumulated_capacity: Decimal

    def validate(self) -> None:
        for field_name in (
            "created_value", "captured_value", "cost", "risk", "debt", "accumulated_capacity"
        ):
            if getattr(self, field_name) < 0:
                raise ValidationError(f"{field_name} must be non-negative")

    @property
    def health_delta(self) -> Decimal:
        self.validate()
        return self.created_value - self.cost - self.risk - self.debt

    @property
    def object_hash(self) -> str:
        self.validate()
        return _canonical_hash({k: str(v) for k, v in asdict(self).items()})


class CaptalsEngine:
    """Fail-closed economic metabolism over verified M-bits and rights.

    It deliberately does not price assets and does not issue tokens.
    """

    def settle(self, m_bit: MBit, rights: RightsObject) -> CaptalsSnapshot:
        m_bit.validate()
        rights.validate()
        if rights.m_bit is None:
            raise ValidationError("settlement requires rights bound to an MBit")
        if rights.m_bit.object_hash != m_bit.object_hash:
            raise ValidationError("rights object and MBit mismatch")

        royalty_rate = rights.economics.get("royalty_rate", Decimal("0"))
        if royalty_rate < 0 or royalty_rate > 1:
            raise ValidationError("royalty_rate must be between 0 and 1")

        captured = m_bit.value_score * royalty_rate
        capacity = max(Decimal("0"), m_bit.value_score - m_bit.cost_computed)
        return CaptalsSnapshot(
            created_value=m_bit.value_score,
            captured_value=captured,
            cost=m_bit.cost_computed,
            risk=Decimal("0"),
            debt=Decimal("0"),
            accumulated_capacity=capacity,
        )
