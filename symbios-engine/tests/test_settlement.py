from decimal import Decimal
from hashlib import sha3_256
import json
import pytest
from core.settlement import EconomicObservation, build_settlement_receipt, prepare_acoa_ledger_event, verify_ledger_chain
from core.valuechain import CaptalsEngine, CaptalsSnapshot, Decision, MBit, MNB, MemBit, MemNanoBit, RightKind, RightsObject, ValidationError

def fixture_objects(risk=Decimal("2"),debt=Decimal("3"),*,suffix="1"):
    mnb=MNB(f"e-settle-{suffix}","runtime","a"*64,"b"*64,f"2026-08-29T03:00:0{suffix}Z"); nano=MemNanoBit(mnb,f"c-settle-{suffix}"); mem=MemBit(nano,Decision.PASS,"c"*64,"policy-v1","key-v1","captals"); mbit=MBit(mem,f"trail-{suffix}",f"milestone-{suffix}",Decimal("100"),{"impact":Decimal("1")},Decimal("10")); rights=RightsObject(f"artifact-{suffix}",mem,frozenset({RightKind.COMMERCIAL_USE}),"matverse","licensee",{"territory":"BR"},{"royalty_rate":Decimal("0.10")},mbit); observation=EconomicObservation(risk,debt,"d"*64,"risk-debt-v1"); snapshot=CaptalsEngine().settle(mbit,rights,risk=risk,debt=debt); return mbit,rights,snapshot,observation

def settlement(sequence=1,previous="GENESIS",*,suffix="1"):
    m,r,s,o=fixture_objects(suffix=suffix); return build_settlement_receipt(m_bit=m,rights=r,snapshot=s,economic_observation=o,policy_version="captals-policy-v1",sequence=sequence,previous_receipt_hash=previous)

def test_settlement_receipt_binds_all_governed_inputs():
    p=settlement().as_payload(); assert len(p["receipt_hash"])==64 and p["m_bit_hash"] and p["rights_hash"] and p["economic_observation_hash"]

def test_risk_and_debt_must_be_measured_not_silent_zero():
    m,r,s,o=fixture_objects(); bad=CaptalsSnapshot(s.created_value,s.captured_value,s.cost,Decimal("0"),Decimal("0"),s.accumulated_capacity)
    with pytest.raises(ValidationError,match="recomputed Captals"): build_settlement_receipt(m_bit=m,rights=r,snapshot=bad,economic_observation=o,policy_version="captals-policy-v1",sequence=1)

def test_forged_captured_value_is_rejected_even_if_snapshot_self_hashes():
    m,r,s,o=fixture_objects(); forged=CaptalsSnapshot(s.created_value,s.captured_value+Decimal("1"),s.cost,s.risk,s.debt,s.accumulated_capacity); assert forged.object_hash!=s.object_hash
    with pytest.raises(ValidationError,match="recomputed Captals"): build_settlement_receipt(m_bit=m,rights=r,snapshot=forged,economic_observation=o,policy_version="captals-policy-v1",sequence=1)

def test_forged_accumulated_capacity_is_rejected_even_if_snapshot_self_hashes():
    m,r,s,o=fixture_objects(); forged=CaptalsSnapshot(s.created_value,s.captured_value,s.cost,s.risk,s.debt,s.accumulated_capacity+Decimal("1")); assert forged.object_hash!=s.object_hash
    with pytest.raises(ValidationError,match="recomputed Captals"): build_settlement_receipt(m_bit=m,rights=r,snapshot=forged,economic_observation=o,policy_version="captals-policy-v1",sequence=1)

def test_non_first_receipt_cannot_reset_to_genesis():
    with pytest.raises(ValidationError,match="previous_receipt_hash"): settlement(sequence=2)

def test_first_receipt_cannot_claim_non_genesis_parent():
    with pytest.raises(ValidationError,match="must start at GENESIS"): settlement(sequence=1,previous="a"*64)

def test_prepare_first_acoa_event_uses_genesis_and_verifies():
    e=prepare_acoa_ledger_event(settlement=settlement(),ts="2026-08-29T03:01:00Z",existing_events=[]); assert e["prev_hash"]=="GENESIS" and verify_ledger_chain([e])==e["hash"]

def test_acoa_hash_matches_legacy_serializer_exactly():
    e=prepare_acoa_ledger_event(settlement=settlement(),ts=1787972460.25,existing_events=[]); body={k:e[k] for k in ("ts","event_type","payload","prev_hash")}; assert e["hash"]==sha3_256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def test_prepare_next_event_requires_distinct_mbit_and_valid_receipt_chain():
    r1=settlement(suffix="1"); e1=prepare_acoa_ledger_event(settlement=r1,ts="2026-08-29T03:01:00Z",existing_events=[]); r2=settlement(sequence=2,previous=r1.receipt_hash,suffix="2"); e2=prepare_acoa_ledger_event(settlement=r2,ts="2026-08-29T03:02:00Z",existing_events=[e1]); assert e2["prev_hash"]==e1["hash"] and verify_ledger_chain([e1,e2])==e2["hash"]

def test_same_mbit_cannot_be_settled_twice():
    r1=settlement(suffix="1"); e1=prepare_acoa_ledger_event(settlement=r1,ts="2026-08-29T03:01:00Z",existing_events=[]); dup=settlement(sequence=2,previous=r1.receipt_hash,suffix="1")
    with pytest.raises(ValidationError,match="MBit already settled"): prepare_acoa_ledger_event(settlement=dup,ts="2026-08-29T03:02:00Z",existing_events=[e1])

def test_corrupted_existing_ledger_blocks_new_event():
    r1=settlement(); e=prepare_acoa_ledger_event(settlement=r1,ts="2026-08-29T03:01:00Z",existing_events=[]); e["payload"]["policy_version"]="tampered"
    with pytest.raises(ValidationError,match="hash mismatch"): prepare_acoa_ledger_event(settlement=settlement(sequence=2,previous=r1.receipt_hash,suffix="2"),ts="x",existing_events=[e])

def test_receipt_payload_tamper_with_rehashed_ledger_still_blocks():
    e=prepare_acoa_ledger_event(settlement=settlement(),ts="x",existing_events=[]); e["payload"]["policy_version"]="tampered"; body={k:e[k] for k in ("ts","event_type","payload","prev_hash")}; e["hash"]=sha3_256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    with pytest.raises(ValidationError,match="receipt hash mismatch"): verify_ledger_chain([e])

def test_ledger_schema_corruption_blocks_instead_of_resetting():
    with pytest.raises(ValidationError,match="schema mismatch"): verify_ledger_chain([{"ts":"x","event_type":"X","payload":{},"prev_hash":"GENESIS"}])
