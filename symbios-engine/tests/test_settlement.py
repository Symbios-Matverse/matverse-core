from decimal import Decimal
from hashlib import sha3_256
import json

import pytest

from core.settlement import EconomicObservation, build_settlement_receipt, prepare_acoa_ledger_event, verify_ledger_chain
from core.valuechain import CaptalsSnapshot, Decision, MBit, MNB, MemBit, MemNanoBit, RightKind, RightsObject, ValidationError


def fixture_objects(risk=Decimal("2"), debt=Decimal("3"), *, suffix="1"):
    mnb = MNB(f"e-settle-{suffix}", "runtime", "a" * 64, "b" * 64, f"2026-08-29T03:00:0{suffix}Z")
    nano = MemNanoBit(mnb, f"c-settle-{suffix}")
    mem = MemBit(nano, Decision.PASS, "c" * 64, "policy-v1", "key-v1", "captals")
    mbit = MBit(mem, f"trail-{suffix}", f"milestone-{suffix}", Decimal("100"), {"impact": Decimal("1")}, Decimal("10"))
    rights = RightsObject(
        f"artifact-{suffix}", mem, frozenset({RightKind.COMMERCIAL_USE}), "matverse", "licensee",
        {"territory": "BR"}, {"royalty_rate": Decimal("0.10")}, mbit,
    )
    snapshot = CaptalsSnapshot(Decimal("100"), Decimal("10"), Decimal("10"), risk, debt, Decimal("90"))
    observation = EconomicObservation(risk, debt, "d" * 64, "risk-debt-v1")
    return mbit, rights, snapshot, observation


def settlement(sequence=1, previous="GENESIS", *, suffix="1"):
    mbit, rights, snapshot, observation = fixture_objects(suffix=suffix)
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
    with pytest.raises(ValidationError, match="previous_receipt_hash"):
        settlement(sequence=2)


def test_first_receipt_cannot_claim_non_genesis_parent():
    with pytest.raises(ValidationError, match="must start at GENESIS"):
        settlement(sequence=1, previous="a" * 64)


def test_prepare_first_acoa_event_uses_genesis_and_verifies():
    event = prepare_acoa_ledger_event(settlement=settlement(), ts="2026-08-29T03:01:00Z", existing_events=[])
    assert event["prev_hash"] == "GENESIS"
    assert verify_ledger_chain([event]) == event["hash"]


def test_acoa_hash_matches_legacy_serializer_exactly():
    event = prepare_acoa_ledger_event(settlement=settlement(), ts=1787972460.25, existing_events=[])
    body = {k: event[k] for k in ("ts", "event_type", "payload", "prev_hash")}
    legacy_raw = json.dumps(body, sort_keys=True, ensure_ascii=False)
    assert event["hash"] == sha3_256(legacy_raw.encode("utf-8")).hexdigest()


def test_prepare_next_event_requires_distinct_mbit_and_valid_receipt_chain():
    first_receipt = settlement(suffix="1")
    first = prepare_acoa_ledger_event(settlement=first_receipt, ts="2026-08-29T03:01:00Z", existing_events=[])
    second_receipt = settlement(sequence=2, previous=first_receipt.receipt_hash, suffix="2")
    second = prepare_acoa_ledger_event(settlement=second_receipt, ts="2026-08-29T03:02:00Z", existing_events=[first])
    assert second["prev_hash"] == first["hash"]
    assert second["payload"]["previous_receipt_hash"] == first_receipt.receipt_hash
    assert verify_ledger_chain([first, second]) == second["hash"]


def test_same_mbit_cannot_be_settled_twice():
    first_receipt = settlement(suffix="1")
    first = prepare_acoa_ledger_event(settlement=first_receipt, ts="2026-08-29T03:01:00Z", existing_events=[])
    duplicate = settlement(sequence=2, previous=first_receipt.receipt_hash, suffix="1")
    with pytest.raises(ValidationError, match="MBit already settled"):
        prepare_acoa_ledger_event(settlement=duplicate, ts="2026-08-29T03:02:00Z", existing_events=[first])


def test_corrupted_existing_ledger_blocks_new_event():
    first_receipt = settlement(suffix="1")
    first = prepare_acoa_ledger_event(settlement=first_receipt, ts="2026-08-29T03:01:00Z", existing_events=[])
    first["payload"]["policy_version"] = "tampered"
    with pytest.raises(ValidationError, match="hash mismatch"):
        prepare_acoa_ledger_event(settlement=settlement(sequence=2, previous=first_receipt.receipt_hash, suffix="2"), ts="2026-08-29T03:02:00Z", existing_events=[first])


def test_receipt_payload_tamper_with_rehashed_ledger_still_blocks():
    first = prepare_acoa_ledger_event(settlement=settlement(), ts="2026-08-29T03:01:00Z", existing_events=[])
    first["payload"]["policy_version"] = "tampered"
    body = {k: first[k] for k in ("ts", "event_type", "payload", "prev_hash")}
    first["hash"] = sha3_256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    with pytest.raises(ValidationError, match="receipt hash mismatch"):
        verify_ledger_chain([first])


def test_ledger_schema_corruption_blocks_instead_of_resetting():
    malformed = {"ts": "x", "event_type": "X", "payload": {}, "prev_hash": "GENESIS"}
    with pytest.raises(ValidationError, match="schema mismatch"):
        verify_ledger_chain([malformed])
