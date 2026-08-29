import base64
from hashlib import sha256
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.authority import AuthorityRecord, AuthorityRegistry, signed_receipt_payload
from core.authority_history import AuthorityEvent, _canonical
from core.authorized_witness import materialize_mem_bit_from_historical_signed_witness, materialize_mem_bit_from_signed_witness
from core.ed25519_crypto import verify_ed25519
from core.valuechain import Decision, MNB, MemNanoBit, ValidationError

ISSUED=1787972000

def receipt(status="PASS", issued_at=ISSUED):
    body={"kind":"scientific_witness","status":status,"subject_hash":"a"*64,"issued_at_unix":issued_at,"details":{"source":"u-kernel"}}
    body["receipt_hash"]=sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return body

def lineage(): return MemNanoBit(MNB("event-authorized","interop-test","b"*64,"c"*64,"2026-08-29T00:00:00Z",{}),"continuity-authorized",())
def kp():
    p=Ed25519PrivateKey.generate(); pem=p.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode(); return p,pem

def signed_fixture(status="PASS"):
    private,pem=kp(); item=receipt(status); payload=signed_receipt_payload(item,signer_key_id="u-kernel-test-v1",authority_scope="captals",policy_version="policy-v1"); sig=base64.b64encode(private.sign(payload)).decode(); reg=AuthorityRegistry({"u-kernel-test-v1":AuthorityRecord("u-kernel-test-v1",pem,frozenset({"captals"}),policy_versions=frozenset({"policy-v1"}))}); return item,sig,reg

def materialize(item,sig,reg,**overrides):
    p=dict(mem_nano_bit=lineage(),receipt=item,signature_b64=sig,signer_key_id="u-kernel-test-v1",authority_scope="captals",policy_version="policy-v1",registry=reg,ed25519_verify=verify_ed25519,accepted_kinds={"scientific_witness"},required_subject_hash="a"*64); p.update(overrides); return materialize_mem_bit_from_signed_witness(**p)

def auth_event(seq,typ,when,signer,pem,previous,authorizer,priv):
    u=AuthorityEvent(seq,typ,when,signer,pem,frozenset({"captals"}),frozenset({"policy-v1"}),previous,authorizer,""); sig=base64.b64encode(priv.sign(_canonical(u.body()))).decode(); return AuthorityEvent(seq,typ,when,signer,pem,u.scopes,u.policy_versions,previous,authorizer,sig)

def historical_fixture(receipt_time=ISSUED, revoke_time=ISSUED+100):
    root,root_pem=kp(); signer,signer_pem=kp(); item=receipt(issued_at=receipt_time)
    grant=auth_event(1,"GRANT",ISSUED-100,"u-kernel-test-v1",signer_pem,"GENESIS","root",root)
    revoke=auth_event(2,"REVOKE",revoke_time,"u-kernel-test-v1",signer_pem,grant.event_hash(),"root",root)
    payload=signed_receipt_payload(item,signer_key_id="u-kernel-test-v1",authority_scope="captals",policy_version="policy-v1"); sig=base64.b64encode(signer.sign(payload)).decode()
    return item,sig,[grant,revoke],root_pem

def hist_materialize(item,sig,events,root_pem):
    return materialize_mem_bit_from_historical_signed_witness(mem_nano_bit=lineage(),receipt=item,signature_b64=sig,signer_key_id="u-kernel-test-v1",authority_scope="captals",policy_version="policy-v1",authority_events=events,root_key_id="root",root_public_key_pem=root_pem,ed25519_verify=verify_ed25519,accepted_kinds={"scientific_witness"},required_subject_hash="a"*64)

def test_atomic_boundary_materializes_only_after_valid_signature_and_authority():
    i,s,r=signed_fixture(); assert materialize(i,s,r).decision_gate is Decision.PASS

def test_bad_signature_blocks_atomic_materialization():
    i,_,r=signed_fixture()
    with pytest.raises(ValidationError,match="signature verification failed"): materialize(i,base64.b64encode(b"x"*64).decode(),r)

def test_scope_mismatch_blocks_atomic_materialization():
    i,s,r=signed_fixture()
    with pytest.raises(ValidationError,match="scope"): materialize(i,s,r,authority_scope="research")

def test_policy_mismatch_blocks_atomic_materialization():
    i,s,r=signed_fixture()
    with pytest.raises(ValidationError,match="policy version"): materialize(i,s,r,policy_version="policy-v2")

def test_block_receipt_never_materializes_even_when_signature_is_valid():
    i,s,r=signed_fixture("BLOCK")
    with pytest.raises(ValidationError,match="cannot materialize"): materialize(i,s,r)

def test_subject_binding_is_enforced_inside_same_boundary():
    i,s,r=signed_fixture()
    with pytest.raises(ValidationError,match="subject"): materialize(i,s,r,required_subject_hash="f"*64)

def test_historical_boundary_accepts_receipt_before_later_revocation():
    i,s,e,r=historical_fixture(); m=hist_materialize(i,s,e,r); assert m.decision_gate is Decision.PASS and m.evidence_hash==i["receipt_hash"]

def test_historical_boundary_blocks_receipt_at_or_after_revocation():
    i,s,e,r=historical_fixture(receipt_time=ISSUED+100,revoke_time=ISSUED+100)
    with pytest.raises(ValidationError,match="revoked"): hist_materialize(i,s,e,r)

def test_historical_boundary_blocks_tampered_authority_chain():
    i,s,e,r=historical_fixture(); bad=e[1]; e[1]=AuthorityEvent(bad.sequence,bad.event_type,bad.effective_at_unix,bad.signer_key_id,bad.public_key_pem,bad.scopes,bad.policy_versions,"f"*64,bad.authorizer_key_id,bad.signature_b64)
    with pytest.raises(ValidationError,match="previous hash mismatch"): hist_materialize(i,s,e,r)
