from decimal import Decimal

import pytest

from core.mmnb import build_mmnb_envelope
from core.settlement import EconomicObservation, build_settlement_receipt, prepare_acoa_ledger_event
from core.valuechain import CaptalsSnapshot, Decision, MBit, MNB, MemBit, MemNanoBit, RightKind, RightsObject, ValidationError


def trajectory():
    mnb = MNB("event-mmnb", "runtime", "a" * 64, "b" * 64, "2026-08-29T03:10:00Z")
    nano = MemNanoBit(mnb, "continuity-mmnb")
    mem = MemBit(nano, Decision.PASS, "c" * 64, "policy-v1", "key-v1", "captals")
    mbit = MBit(mem, "trail-mmnb", "milestone-mmnb", Decimal("100"), {"impact": Decimal("1")}, Decimal("10"))
    rights = RightsObject(
        "artifact-mmnb", mem, frozenset({RightKind.COMMERCIAL_USE}), "matverse", "licensee",
        {"territory": "BR"}, {"royalty_rate": Decimal("0.10")}, mbit,
    )
    obs = EconomicObservation(Decimal("2"), Decimal("3"), "d" * 64, "risk-debt-v1")
    snapshot = CaptalsSnapshot(Decimal("100"), Decimal("10"), Decimal("10"), Decimal("2"), Decimal("3"), Decimal("90"))
    receipt = build_settlement_receipt(
        m_bit=mbit, rights=rights, snapshot=snapshot, economic_observation=obs,
        policy_version="captals-policy-v1", sequence=1,
    )
    event = prepare_acoa_ledger_event(settlement=receipt, ts="2026-08-29T03:11:00Z", existing_events=[])
    return mnb, nano, mem, mbit, rights, obs, receipt, [event]


def test_full_trajectory_builds_deterministic_mmnb_envelope():
    args = trajectory()
    a = build_mmnb_envelope(mnb=args[0], mem_nano_bit=args[1], mem_bit=args[2], m_bit=args[3], rights=args[4], economic_observation=args[5], settlement=args[6], ledger_events=args[7])
    b = build_mmnb_envelope(mnb=args[0], mem_nano_bit=args[1], mem_bit=args[2], m_bit=args[3], rights=args[4], economic_observation=args[5], settlement=args[6], ledger_events=args[7])
    assert a.envelope_hash == b.envelope_hash
    assert a.ledger_tip_hash == args[7][-1]["hash"]


def test_mmnb_blocks_missing_persisted_ledger_event():
    args = trajectory()
    with pytest.raises(ValidationError, match="persisted settlement"):
        build_mmnb_envelope(mnb=args[0], mem_nano_bit=args[1], mem_bit=args[2], m_bit=args[3], rights=args[4], economic_observation=args[5], settlement=args[6], ledger_events=[])


def test_mmnb_blocks_tampered_ledger():
    args = trajectory()
    args[7][0]["payload"]["policy_version"] = "tampered"
    with pytest.raises(ValidationError, match="hash mismatch"):
        build_mmnb_envelope(mnb=args[0], mem_nano_bit=args[1], mem_bit=args[2], m_bit=args[3], rights=args[4], economic_observation=args[5], settlement=args[6], ledger_events=args[7])


def test_mmnb_blocks_wrong_mnb_lineage():
    args = trajectory()
    other = MNB("other", "runtime", "a" * 64, "b" * 64, "2026-08-29T03:10:00Z")
    with pytest.raises(ValidationError, match="MNB -> MemNanoBit"):
        build_mmnb_envelope(mnb=other, mem_nano_bit=args[1], mem_bit=args[2], m_bit=args[3], rights=args[4], economic_observation=args[5], settlement=args[6], ledger_events=args[7])


def test_mmnb_blocks_wrong_economic_observation():
    args = trajectory()
    other_obs = EconomicObservation(Decimal("7"), Decimal("3"), "e" * 64, "risk-debt-v1")
    with pytest.raises(ValidationError, match="EconomicObservation -> Settlement"):
        build_mmnb_envelope(mnb=args[0], mem_nano_bit=args[1], mem_bit=args[2], m_bit=args[3], rights=args[4], economic_observation=other_obs, settlement=args[6], ledger_events=args[7])


def test_mmnb_requires_exactly_one_matching_settlement_event():
    args = trajectory()
    duplicate = dict(args[7][0])
    duplicate["prev_hash"] = args[7][0]["hash"]
    # The duplicate cannot simply reuse the old hash; chain verification must fail first.
    with pytest.raises(ValidationError):
        build_mmnb_envelope(mnb=args[0], mem_nano_bit=args[1], mem_bit=args[2], m_bit=args[3], rights=args[4], economic_observation=args[5], settlement=args[6], ledger_events=[args[7][0], duplicate])
