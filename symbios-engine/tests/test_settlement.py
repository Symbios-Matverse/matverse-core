from decimal import Decimal
from hashlib import sha3_256
import json

import pytest

from core.settlement import EconomicObservation, build_settlement_receipt, prepare_acoa_ledger_event, verify_ledger_chain
from core.valuechain import CaptalsSnapshot, Decision, MBit, MNB, MemBit, MemNanoBit, RightKind, RightsObject, ValidationError


def fixture_objects(risk=Decimal("2"), debt=Decimal("3")):
    mnb = MNB("e-settle", "runtime", "a" * 64, "b" * 64, "2026-08-29T03:00:00Z")
    nano = MemNanoBit(mnb, "c-settle")
    mem = MemBit(nano, Decision.PASS, "c" * 64, "policy-v1", "key-v1", "captals")
    mbit = MBit(mem, "trail-1", "milestone-1", Decimal("100"), {"impact": Decimal("1")}, Decimal("10"))
    rights = RightsObject(
        "artifact-1", mem, frozenset({RightKind.COMMERCIAL_USE}), "matverse", "licensee",
        {"territory": "BR"}, {"royalty_rate": Decimal("0.10")}, mbit,
    )
    snapshot = CaptalsSnapshot(Decimal("100"), Decimal("10"), Decimal("10"), risk, debt, Decimal("90"))
    observation = EconomicObservation(risk, debt, "d" * 64, "risk-debt-v1")
    return mbit, rights, snapshot, observation


def settlement(sequence=1, previous="GENESIS"):
    mbit, rights, snapshot, observation = fixture_objects()
    return build_settlement_receipt(
        m_bit=mbit, rights=rights, snapshot=snapshot, economic_observation=observation,
        policy_version="captals-policy-v1", sequence=sequence, previous_receipt_hash=previous,
    )


def test_settlement_receipt_binds_all_governed_inputs():
    receipt = settlement()
    payload = receipt.as_payload()
    assert len(payload["receipt_hash"]) == 64
    assert payload["m_bit_hash"]
    assert payload["rights_hash"]
    assert payload["economic_observation_hash"]


def test_risk_and_debt_must_be_measured_not_silent_zero():
    mbit, rights, snapshot, observation = fixture_objects()
    bad_snapshot = CaptalsSnapshot(snapshot.created_value, snapshot.captured_value, snapshot.cost, Decimal("0"), Decimal("0"), snapshot.accumulated_capacity)
    with pytest.raises(ValidationError, match="risk/debt"):
        build_settlement_receipt(
            m_bit=mbit, rights=rights, snapshot=bad_snapshot, economic_observation=observation,
            policy_version="captals-policy-v1", sequence=1,
        )


def test_non_first_receipt_cannot_reset_to_genesis():
    with pytest.raises(ValidationError, match="requires previous hash"):
        settlement(sequence=2)


def test_first_receipt_cannot_claim_non_genesis_parent():
    with pytest.raises(ValidationError, match="must start at GENESIS"):
        settlement(sequence=1, previous="a" * 64)


def test_prepare_first_acoa_event_uses_genesis_and_verifies():
    event = prepare_acoa_ledger_event(settlement=settlement(), ts="2026-08-29T03:01:00Z", existing_events=[])
    assert event["prev_hash"] == "GENESIS"
    assert verify_ledger_chain([event]) == event["hash"]


def test_prepare_next_event_requires_valid_existing_chain():
    first = prepare_acoa_ledger_event(settlement=settlement(), ts="2026-08-29T03:01:00Z", existing_events=[])
    second_receipt = settlement(sequence=2, previous=settlement().receipt_hash)
    second = prepare_acoa_ledger_event(settlement=second_receipt, ts="2026-08-29T03:02:00Z", existing_events=[first])
    assert second["prev_hash"] == first["hash"]
    assert verify_ledger_chain([first, second]) == second["hash"]


def test_corrupted_existing_ledger_blocks_new_event():
    first = prepare_acoa_ledger_event(settlement=settlement(), ts="2026-08-29T03:01:00Z", existing_events=[])
    first["payload"]["policy_version"] = "tampered"
    with pytest.raises(ValidationError, match="hash mismatch"):
        prepare_acoa_ledger_event(settlement=settlement(sequence=2, previous=settlement().receipt_hash), ts="2026-08-29T03:02:00Z", existing_events=[first])


def test_ledger_schema_corruption_blocks_instead_of_resetting():
    malformed = {"ts": "x", "event_type": "X", "payload": {}, "prev_hash": "GENESIS"}
    with pytest.raises(ValidationError, match="schema mismatch"):
        verify_ledger_chain([malformed])
