import base64
from hashlib import sha256
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.authority import AuthorityRecord, AuthorityRegistry, signed_receipt_payload
from core.authorized_witness import materialize_mem_bit_from_signed_witness
from core.ed25519_crypto import verify_ed25519
from core.valuechain import Decision, MNB, MemNanoBit, ValidationError


def receipt(status="PASS"):
    body = {
        "kind": "scientific_witness",
        "status": status,
        "subject_hash": "a" * 64,
        "issued_at_unix": 1787972000,
        "details": {"source": "u-kernel"},
    }
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["receipt_hash"] = sha256(raw.encode("utf-8")).hexdigest()
    return body


def lineage():
    mnb = MNB("event-authorized", "interop-test", "b" * 64, "c" * 64, "2026-08-29T00:00:00Z", {})
    return MemNanoBit(mnb, "continuity-authorized", ())


def signed_fixture(*, status="PASS", scope="captals", policy="policy-v1"):
    private = Ed25519PrivateKey.generate()
    public_pem = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    item = receipt(status)
    payload = signed_receipt_payload(item, signer_key_id="u-kernel-test-v1", authority_scope=scope, policy_version=policy)
    signature_b64 = base64.b64encode(private.sign(payload)).decode("ascii")
    registry = AuthorityRegistry({
        "u-kernel-test-v1": AuthorityRecord(
            signer_key_id="u-kernel-test-v1",
            public_key_pem=public_pem,
            scopes=frozenset({"captals"}),
            policy_versions=frozenset({"policy-v1"}),
        )
    })
    return item, signature_b64, registry


def materialize(item, signature_b64, registry, **overrides):
    params = dict(
        mem_nano_bit=lineage(), receipt=item, signature_b64=signature_b64,
        signer_key_id="u-kernel-test-v1", authority_scope="captals",
        policy_version="policy-v1", registry=registry, ed25519_verify=verify_ed25519,
        accepted_kinds={"scientific_witness"}, required_subject_hash="a" * 64,
    )
    params.update(overrides)
    return materialize_mem_bit_from_signed_witness(**params)


def test_atomic_boundary_materializes_only_after_valid_signature_and_authority():
    item, signature_b64, registry = signed_fixture()
    mem_bit = materialize(item, signature_b64, registry)
    assert mem_bit.decision_gate is Decision.PASS
    assert mem_bit.evidence_hash == item["receipt_hash"]
    assert mem_bit.signer_key_id == "u-kernel-test-v1"
    assert mem_bit.authority_scope == "captals"
    assert mem_bit.policy_version == "policy-v1"


def test_bad_signature_blocks_atomic_materialization():
    item, _, registry = signed_fixture()
    bad = base64.b64encode(b"x" * 64).decode("ascii")
    with pytest.raises(ValidationError, match="signature verification failed"):
        materialize(item, bad, registry)


def test_scope_mismatch_blocks_atomic_materialization():
    item, signature_b64, registry = signed_fixture()
    with pytest.raises(ValidationError, match="scope"):
        materialize(item, signature_b64, registry, authority_scope="research")


def test_policy_mismatch_blocks_atomic_materialization():
    item, signature_b64, registry = signed_fixture()
    with pytest.raises(ValidationError, match="policy version"):
        materialize(item, signature_b64, registry, policy_version="policy-v2")


def test_block_receipt_never_materializes_even_when_signature_is_valid():
    item, signature_b64, registry = signed_fixture(status="BLOCK")
    with pytest.raises(ValidationError, match="cannot materialize"):
        materialize(item, signature_b64, registry)


def test_subject_binding_is_enforced_inside_same_boundary():
    item, signature_b64, registry = signed_fixture()
    with pytest.raises(ValidationError, match="subject"):
        materialize(item, signature_b64, registry, required_subject_hash="f" * 64)
