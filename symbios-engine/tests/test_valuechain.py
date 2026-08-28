from decimal import Decimal

import pytest

from core.valuechain import (
    CaptalsEngine,
    Decision,
    MBit,
    MNB,
    MemBit,
    MemNanoBit,
    RightKind,
    RightsObject,
    ValidationError,
)


def chain(decision=Decision.PASS):
    mnb = MNB("e1", "sensor", "c" * 64, "d" * 64, "2026-08-28T00:00:00Z")
    nano = MemNanoBit(mnb, "cont-1", ("r1",))
    mem = MemBit(nano, decision, "e" * 64, "p1", "key1", "scope1")
    return mnb, nano, mem


def test_inclusion_hashes_are_deterministic():
    mnb, nano, mem = chain()
    assert mnb.object_hash == mnb.object_hash
    assert nano.object_hash == nano.object_hash
    assert mem.object_hash == mem.object_hash


def test_mbit_requires_pass_membit():
    _, _, mem = chain(Decision.HOLD)
    with pytest.raises(ValidationError):
        MBit(mem, "trail", "ms", Decimal("1"), {}).validate()


def test_rights_can_exist_before_realized_value():
    _, _, mem = chain()
    rights = RightsObject(
        "artifact-1",
        mem,
        frozenset({RightKind.USE}),
        "licensor",
        "licensee",
        {"duration_days": 30},
    )
    rights.validate()
    assert rights.m_bit is None


def test_rights_mbit_must_share_membit():
    _, _, mem1 = chain()
    mbit = MBit(mem1, "trail", "milestone", Decimal("10"), {})

    mnb = MNB("e2", "sensor", "a" * 64, "b" * 64, "2026-08-28T00:00:01Z")
    nano = MemNanoBit(mnb, "cont-2")
    mem2 = MemBit(nano, Decision.PASS, "f" * 64, "p1", "key2", "scope1")

    rights = RightsObject(
        "artifact-1",
        mem2,
        frozenset({RightKind.USE}),
        "licensor",
        "licensee",
        {},
        m_bit=mbit,
    )
    with pytest.raises(ValidationError):
        rights.validate()


def test_captals_settlement():
    _, _, mem = chain()
    mbit = MBit(
        mem,
        "trail",
        "milestone",
        Decimal("100"),
        {"impact": Decimal("1")},
        Decimal("20"),
    )
    rights = RightsObject(
        "artifact-1",
        mem,
        frozenset({RightKind.COMMERCIAL_USE}),
        "licensor",
        "licensee",
        {},
        {"royalty_rate": Decimal("0.10")},
        mbit,
    )
    snapshot = CaptalsEngine().settle(mbit, rights)
    assert snapshot.created_value == Decimal("100")
    assert snapshot.captured_value == Decimal("10.00")
    assert snapshot.accumulated_capacity == Decimal("80")


def test_bad_royalty_rate_blocks():
    _, _, mem = chain()
    mbit = MBit(mem, "trail", "milestone", Decimal("100"), {})
    rights = RightsObject(
        "artifact-1",
        mem,
        frozenset({RightKind.USE}),
        "licensor",
        "licensee",
        {},
        {"royalty_rate": Decimal("1.5")},
        mbit,
    )
    with pytest.raises(ValidationError):
        CaptalsEngine().settle(mbit, rights)
