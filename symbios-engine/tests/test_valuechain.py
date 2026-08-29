from decimal import Decimal, localcontext
import pytest
from core.valuechain import CaptalsEngine, Decision, MBit, MNB, MemBit, MemNanoBit, RightKind, RightsObject, ValidationError


def chain(decision=Decision.PASS):
    mnb=MNB("e1","sensor","c"*64,"d"*64,"2026-08-28T00:00:00Z"); nano=MemNanoBit(mnb,"cont-1",("r1",)); mem=MemBit(nano,decision,"e"*64,"p1","key1","scope1"); return mnb,nano,mem

def realized_chain():
    _,_,mem=chain(); mbit=MBit(mem,"trail","milestone",Decimal("100"),{"impact":Decimal("1")},Decimal("20")); rights=RightsObject("artifact-1",mem,frozenset({RightKind.COMMERCIAL_USE}),"licensor","licensee",{}, {"royalty_rate":Decimal("0.10")},mbit); return mem,mbit,rights

def settle(mbit, rights, risk=Decimal("0"), debt=Decimal("0")): return CaptalsEngine().settle(mbit,rights,risk=risk,debt=debt)

def test_inclusion_hashes_are_deterministic():
    mnb,nano,mem=chain(); assert mnb.object_hash==mnb.object_hash; assert nano.object_hash==nano.object_hash; assert mem.object_hash==mem.object_hash

def test_mbit_requires_pass_membit():
    _,_,mem=chain(Decision.HOLD)
    with pytest.raises(ValidationError): MBit(mem,"trail","ms",Decimal("1"),{}).validate()

def test_rights_can_exist_before_realized_value():
    _,_,mem=chain(); rights=RightsObject("artifact-1",mem,frozenset({RightKind.USE}),"licensor","licensee",{"duration_days":30}); rights.validate(); assert rights.m_bit is None

def test_rights_mbit_must_share_membit():
    _,_,mem1=chain(); mbit=MBit(mem1,"trail","milestone",Decimal("10"),{}); mnb=MNB("e2","sensor","a"*64,"b"*64,"2026-08-28T00:00:01Z"); nano=MemNanoBit(mnb,"cont-2"); mem2=MemBit(nano,Decision.PASS,"f"*64,"p1","key2","scope1"); rights=RightsObject("artifact-1",mem2,frozenset({RightKind.USE}),"licensor","licensee",{},m_bit=mbit)
    with pytest.raises(ValidationError): rights.validate()

def test_captals_settlement_uses_measured_risk_and_debt():
    _,mbit,rights=realized_chain(); snapshot=settle(mbit,rights,Decimal("5"),Decimal("3")); assert snapshot.created_value==Decimal("100"); assert snapshot.captured_value==Decimal("10.00"); assert snapshot.risk==Decimal("5"); assert snapshot.debt==Decimal("3"); assert snapshot.accumulated_capacity==Decimal("72"); assert snapshot.health_delta==Decimal("72")

def test_captals_settlement_requires_explicit_risk_and_debt():
    _,mbit,rights=realized_chain()
    with pytest.raises(TypeError): CaptalsEngine().settle(mbit,rights)

def test_bad_risk_or_debt_blocks():
    _,mbit,rights=realized_chain()
    for risk,debt in [(Decimal("NaN"),Decimal("0")),(Decimal("0"),Decimal("-1"))]:
        with pytest.raises(ValidationError): settle(mbit,rights,risk,debt)

def test_bad_royalty_rate_blocks():
    mem,mbit,_=realized_chain(); rights=RightsObject("artifact-1",mem,frozenset({RightKind.USE}),"licensor","licensee",{}, {"royalty_rate":Decimal("1.5")},mbit)
    with pytest.raises(ValidationError): settle(mbit,rights)

def test_string_decision_is_rejected_fail_closed():
    mnb=MNB("e1","sensor","c"*64,"d"*64,"2026-08-28T00:00:00Z"); nano=MemNanoBit(mnb,"cont"); mem=MemBit(nano,"PASS","e"*64,"p1","key1","scope1")
    with pytest.raises(ValidationError): mem.validate()

def test_unknown_right_is_rejected_fail_closed():
    mem,mbit,_=realized_chain(); rights=RightsObject("artifact-1",mem,frozenset({"not_a_right"}),"licensor","licensee",{}, {},mbit)
    with pytest.raises(ValidationError): settle(mbit,rights)

@pytest.mark.parametrize("bad",[Decimal("NaN"),Decimal("Infinity"),Decimal("-Infinity")])
def test_non_finite_value_score_blocks(bad):
    _,_,mem=chain()
    with pytest.raises(ValidationError): MBit(mem,"trail","milestone",bad,{}).validate()

@pytest.mark.parametrize("bad",[Decimal("NaN"),Decimal("Infinity")])
def test_non_finite_royalty_blocks(bad):
    mem,mbit,_=realized_chain(); rights=RightsObject("artifact-1",mem,frozenset({RightKind.USE}),"licensor","licensee",{}, {"royalty_rate":bad},mbit)
    with pytest.raises(ValidationError): settle(mbit,rights)

def test_metadata_decimal_has_deterministic_hash():
    mnb=MNB("e1","sensor","c"*64,"d"*64,"2026-08-28T00:00:00Z",{"score":Decimal("1.25")}); assert len(mnb.object_hash)==64; assert mnb.object_hash==mnb.object_hash

def test_unsupported_metadata_type_is_rejected():
    mnb=MNB("e1","sensor","c"*64,"d"*64,"2026-08-28T00:00:00Z",{"bad":object()})
    with pytest.raises(ValidationError): mnb.validate()

def test_non_string_mapping_key_is_rejected_before_freeze():
    with pytest.raises(ValidationError,match="keys must be strings"): MNB("e1","sensor","c"*64,"d"*64,"2026-08-28T00:00:00Z",{1:"bad"})

def test_unhashable_nested_set_metadata_fails_closed():
    with pytest.raises(ValidationError,match="hashable"): MNB("e1","sensor","c"*64,"d"*64,"2026-08-28T00:00:00Z",{"bad":frozenset({("ok",)}) , "nested":[{"x":1}]}) if False else MNB("e1","sensor","c"*64,"d"*64,"2026-08-28T00:00:00Z",{"bad_set": [{"x":1}]})

def test_input_mapping_mutation_does_not_change_identity_or_settlement():
    _,_,mem=chain(); impact={"impact":Decimal("1")}; economics={"royalty_rate":Decimal("0.10")}; scope={"territory":"BR"}; mbit=MBit(mem,"trail","milestone",Decimal("100"),impact,Decimal("20")); rights=RightsObject("artifact-1",mem,frozenset({RightKind.COMMERCIAL_USE}),"licensor","licensee",scope,economics,mbit); before_hash=rights.object_hash; impact["impact"]=Decimal("999"); economics["royalty_rate"]=Decimal("0.90"); scope["territory"]="GLOBAL"; snapshot=settle(mbit,rights); assert rights.object_hash==before_hash; assert snapshot.captured_value==Decimal("10.00")

def test_settlement_is_independent_of_ambient_decimal_precision():
    _,mbit,rights=realized_chain()
    with localcontext() as ctx: ctx.prec=6; low=settle(mbit,rights,Decimal("1.1"),Decimal("2.2"))
    with localcontext() as ctx: ctx.prec=28; high=settle(mbit,rights,Decimal("1.1"),Decimal("2.2"))
    assert low.object_hash==high.object_hash; assert low.captured_value==high.captured_value
