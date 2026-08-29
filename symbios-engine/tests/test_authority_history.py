import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.authority_history import AuthorityEvent, registry_at, verify_authority_history, _canonical
from core.ed25519_crypto import verify_ed25519
from core.valuechain import ValidationError


def keypair():
    private=Ed25519PrivateKey.generate()
    pem=private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return private,pem


def event(seq, typ, when, signer, pem, previous, authorizer, authorizer_private):
    unsigned=AuthorityEvent(seq,typ,when,signer,pem,frozenset({"captals"}),frozenset({"policy-v1"}),previous,authorizer,"")
    sig=base64.b64encode(authorizer_private.sign(_canonical(unsigned.body()))).decode()
    return AuthorityEvent(seq,typ,when,signer,pem,unsigned.scopes,unsigned.policy_versions,previous,authorizer,sig)


def history():
    root,root_pem=keypair(); a,a_pem=keypair(); a2,a2_pem=keypair()
    e1=event(1,"GRANT",100,"a",a_pem,"GENESIS","root",root)
    e2=event(2,"ROTATE",200,"a",a2_pem,e1.event_hash(),"root",root)
    e3=event(3,"SUSPEND",300,"a",a2_pem,e2.event_hash(),"root",root)
    e4=event(4,"RESUME",400,"a",a2_pem,e3.event_hash(),"root",root)
    e5=event(5,"REVOKE",500,"a",a2_pem,e4.event_hash(),"root",root)
    return root_pem,[e1,e2,e3,e4,e5],a_pem,a2_pem


def test_full_signed_history_verifies():
    root_pem,events,_,_=history()
    assert len(verify_authority_history(events, root_key_id="root", root_public_key_pem=root_pem, ed25519_verify=verify_ed25519)) == 5


def test_registry_reconstructs_historical_key_and_state():
    root_pem,events,a_pem,a2_pem=history()
    assert registry_at(events,at_unix=150,root_key_id="root",root_public_key_pem=root_pem,ed25519_verify=verify_ed25519)._records["a"].public_key_pem == a_pem
    assert registry_at(events,at_unix=250,root_key_id="root",root_public_key_pem=root_pem,ed25519_verify=verify_ed25519)._records["a"].public_key_pem == a2_pem
    assert registry_at(events,at_unix=350,root_key_id="root",root_public_key_pem=root_pem,ed25519_verify=verify_ed25519)._records["a"].status == "SUSPENDED"
    assert registry_at(events,at_unix=450,root_key_id="root",root_public_key_pem=root_pem,ed25519_verify=verify_ed25519)._records["a"].status == "ACTIVE"
    assert registry_at(events,at_unix=550,root_key_id="root",root_public_key_pem=root_pem,ed25519_verify=verify_ed25519)._records["a"].status == "REVOKED"


def test_tampered_event_signature_blocks():
    root_pem,events,_,_=history(); e=events[1]
    events[1]=AuthorityEvent(e.sequence,e.event_type,e.effective_at_unix,e.signer_key_id,e.public_key_pem,e.scopes,e.policy_versions,e.previous_event_hash,e.authorizer_key_id,base64.b64encode(b"x"*64).decode())
    with pytest.raises(ValidationError,match="signature verification failed"):
        verify_authority_history(events,root_key_id="root",root_public_key_pem=root_pem,ed25519_verify=verify_ed25519)


def test_broken_hash_chain_blocks():
    root_pem,events,_,_=history(); e=events[1]
    events[1]=AuthorityEvent(e.sequence,e.event_type,e.effective_at_unix,e.signer_key_id,e.public_key_pem,e.scopes,e.policy_versions,"a"*64,e.authorizer_key_id,e.signature_b64)
    with pytest.raises(ValidationError,match="previous hash mismatch"):
        verify_authority_history(events,root_key_id="root",root_public_key_pem=root_pem,ed25519_verify=verify_ed25519)


def test_non_monotonic_time_blocks():
    root,root_pem=keypair(); a,a_pem=keypair(); b,b_pem=keypair()
    e1=event(1,"GRANT",200,"a",a_pem,"GENESIS","root",root)
    e2=event(2,"GRANT",100,"b",b_pem,e1.event_hash(),"root",root)
    with pytest.raises(ValidationError,match="time is not monotonic"):
        verify_authority_history([e1,e2],root_key_id="root",root_public_key_pem=root_pem,ed25519_verify=verify_ed25519)


def test_revoked_authority_cannot_authorize_later_event():
    root,root_pem=keypair(); a,a_pem=keypair(); b,b_pem=keypair()
    e1=event(1,"GRANT",100,"a",a_pem,"GENESIS","root",root)
    e2=event(2,"REVOKE",200,"a",a_pem,e1.event_hash(),"root",root)
    e3=event(3,"GRANT",300,"b",b_pem,e2.event_hash(),"a",a)
    with pytest.raises(ValidationError,match="authorizer is not active"):
        verify_authority_history([e1,e2,e3],root_key_id="root",root_public_key_pem=root_pem,ed25519_verify=verify_ed25519)
