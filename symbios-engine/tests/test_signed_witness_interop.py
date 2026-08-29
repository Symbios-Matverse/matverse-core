import base64
from hashlib import sha256
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.authority import AuthorityRecord, AuthorityRegistry, signed_receipt_payload, verify_signed_witness_authority
from core.ed25519_crypto import verify_ed25519
from core.valuechain import MNB, MemNanoBit, ValidationError
from core.witness_adapter import materialize_mem_bit_from_witness


def _receipt():
    body = {
        "kind": "scientific_witness",
        "status": "PASS",
        "subject_hash": "a" * 64,
        "issued_at_unix": 1787972000,
        "details": {"source": "u-kernel"},
    }
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["receipt_hash"] = sha256(raw.encode()).hexdigest()
    return body


def _lineage():
    mnb = MNB("event-1", "interop-test", "b" * 64, "c" * 64, "2026-08-29T00:00:00Z", {})
    mnb.validate()
    nano = MemNanoBit(mnb, "continuity-1", ())
    nano.validate()
    return nano


def _signed_fixture(scope="captals", policy="policy-v1"):
    private = Ed25519PrivateKey.generate()
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    receipt = _receipt()
    payload = signed_receipt_payload(receipt, signer_key_id="u-kernel-test-v1", authority_scope=scope, policy_version=policy)
    signature_b64 = base64.b64encode(private.sign(payload)).decode("ascii")
    registry = AuthorityRegistry({
        "u-kernel-test-v1": AuthorityRecord(
            signer_key_id="u-kernel-test-v1",
            public_key_pem=public_pem,
            scopes=frozenset({"captals"}),
            policy_versions=frozenset({"policy-v1"}),
        )
    })
    return receipt, signature_b64, registry


def test_u_kernel_contract_to_authorized_mem_bit():
    receipt, signature_b64, registry = _signed_fixture()
    verified_hash = verify_signed_witness_authority(
        receipt=receipt,
        signature_b64=signature_b64,
        signer_key_id="u-kernel-test-v1",
        authority_scope="captals",
        policy_version="policy-v1",
        registry=registry,
        ed25519_verify=verify_ed25519,
    )
    mem_bit = materialize_mem_bit_from_witness(
        mem_nano_bit=_lineage(), receipt=receipt, policy_version="policy-v1",
        signer_key_id="u-kernel-test-v1", authority_scope="captals",
        required_subject_hash="a" * 64,
    )
    assert mem_bit.evidence_hash == verified_hash
    assert mem_bit.signer_key_id == "u-kernel-test-v1"
    assert mem_bit.authority_scope == "captals"
    assert mem_bit.policy_version == "policy-v1"


def test_signature_tamper_blocks_before_mem_bit():
    receipt, signature_b64, registry = _signed_fixture()
    bad = base64.b64encode(b"x" * 64).decode("ascii")
    with pytest.raises(ValidationError, match="signature verification failed"):
        verify_signed_witness_authority(receipt=receipt, signature_b64=bad, signer_key_id="u-kernel-test-v1", authority_scope="captals", policy_version="policy-v1", registry=registry, ed25519_verify=verify_ed25519)


def test_scope_mismatch_blocks():
    receipt, signature_b64, registry = _signed_fixture()
    with pytest.raises(ValidationError, match="scope"):
        verify_signed_witness_authority(receipt=receipt, signature_b64=signature_b64, signer_key_id="u-kernel-test-v1", authority_scope="research", policy_version="policy-v1", registry=registry, ed25519_verify=verify_ed25519)
