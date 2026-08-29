from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Context, Decimal, localcontext
from enum import Enum
from hashlib import sha256
import json
from types import MappingProxyType
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


_SETTLEMENT_CONTEXT = Context(prec=50)


def _require_nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")


def _require_decimal(name: str, value: Any, *, non_negative: bool = True) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{name} must be a Decimal")
    if not value.is_finite():
        raise ValidationError(f"{name} must be finite")
    if non_negative and value < 0:
        raise ValidationError(f"{name} must be non-negative")
    return value


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, Decimal):
        _require_decimal("metadata Decimal", value, non_negative=False)
        return {"$decimal": str(value)}
    if isinstance(value, Enum):
        return {"$enum": f"{value.__class__.__name__}:{value.value}"}
    if isinstance(value, Mapping):
        if any(not isinstance(k, str) for k in value):
            raise ValidationError("metadata mapping keys must be strings")
        return {k: _canonicalize(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(v) for v in value]
    if isinstance(value, (set, frozenset)):
        normalized = [_canonicalize(v) for v in value]
        return sorted(normalized, key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")))
    raise ValidationError(f"unsupported canonical metadata type: {type(value).__name__}")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(v) for v in value)
    return value


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    normalized = _canonicalize(payload)
    raw = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MNB:
    event_id: str
    source: str
    content_hash: str
    context_hash: str
    timestamp: str
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance", _freeze(self.provenance))

    def validate(self) -> None:
        for name in ("event_id", "source", "content_hash", "context_hash", "timestamp"):
            _require_nonempty(name, getattr(self, name))
        _canonicalize(self.provenance)

    @property
    def object_hash(self) -> str:
        self.validate()
        return _canonical_hash({
            "event_id": self.event_id,
            "source": self.source,
            "content_hash": self.content_hash,
            "context_hash": self.context_hash,
            "timestamp": self.timestamp,
            "provenance": self.provenance,
        })


@dataclass(frozen=True)
class MemNanoBit:
    mnb: MNB
    continuity_id: str
    relation_hashes: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "relation_hashes", tuple(self.relation_hashes))

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
        if not isinstance(self.decision_gate, Decision):
            raise ValidationError("decision_gate must be a Decision")
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "impact_metrics", _freeze(self.impact_metrics))

    def validate(self) -> None:
        self.mem_bit.validate()
        if self.mem_bit.decision_gate != Decision.PASS:
            raise ValidationError("MBit requires a PASS MemBit")
        for name in ("trail_id", "milestone_id"):
            _require_nonempty(name, getattr(self, name))
        _require_decimal("value_score", self.value_score)
        _require_decimal("cost_computed", self.cost_computed)
        for key, value in self.impact_metrics.items():
            _require_nonempty("impact metric key", key)
            _require_decimal(f"impact_metrics[{key}]", value)

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

    def __post_init__(self) -> None:
        object.__setattr__(self, "rights", frozenset(self.rights))
        object.__setattr__(self, "scope", _freeze(self.scope))
        object.__setattr__(self, "economics", _freeze(self.economics))

    def validate(self) -> None:
        self.mem_bit.validate()
        for name in ("artifact_id", "licensor", "licensee"):
            _require_nonempty(name, getattr(self, name))
        if not self.rights:
            raise ValidationError("at least one right is required")
        if any(not isinstance(right, RightKind) for right in self.rights):
            raise ValidationError("rights must contain only RightKind values")
        _canonicalize(self.scope)
        for key, value in self.economics.items():
            _require_nonempty("economics key", key)
            _require_decimal(f"economics[{key}]", value)
        if self.m_bit is not None:
            self.m_bit.validate()
            if self.m_bit.mem_bit.object_hash != self.mem_bit.object_hash:
                raise ValidationError("m_bit must derive from the same mem_bit")

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
            _require_decimal(field_name, getattr(self, field_name))

    @property
    def health_delta(self) -> Decimal:
        self.validate()
        with localcontext(_SETTLEMENT_CONTEXT):
            return self.created_value - self.cost - self.risk - self.debt

    @property
    def object_hash(self) -> str:
        self.validate()
        return _canonical_hash({
            "created_value": str(self.created_value),
            "captured_value": str(self.captured_value),
            "cost": str(self.cost),
            "risk": str(self.risk),
            "debt": str(self.debt),
            "accumulated_capacity": str(self.accumulated_capacity),
        })


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
        _require_decimal("royalty_rate", royalty_rate)
        if royalty_rate > 1:
            raise ValidationError("royalty_rate must be between 0 and 1")

        with localcontext(_SETTLEMENT_CONTEXT):
            captured = m_bit.value_score * royalty_rate
            capacity = max(Decimal("0"), m_bit.value_score - m_bit.cost_computed)

        snapshot = CaptalsSnapshot(
            created_value=m_bit.value_score,
            captured_value=captured,
            cost=m_bit.cost_computed,
            risk=Decimal("0"),
            debt=Decimal("0"),
            accumulated_capacity=capacity,
        )
        snapshot.validate()
        return snapshot
