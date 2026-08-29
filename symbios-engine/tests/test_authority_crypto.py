import base64
from hashlib import sha256
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from core.authority import AuthorityRecord, AuthorityRegistry, signed_receipt_payload, verify_signed_witness_authority
from core.ed25519_crypto import verify_ed25519
from core.valuechain import ValidationError


def witness_receipt():
    body = {
        "kind": "scientific_witness",
        "status": "PASS",
        "subject_hash": "a" * 64,
        "issued_at_unix": 1787972000,
        "details": {"source": "u-kernel-compatible"},
    }
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["receipt_hash"] = sha256(raw.encode("utf-8")).hexdigest()
    return body


def keypair():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_key, public_pem


def test_real_ed25519_signed_witness_passes():
    private_key, public_pem = keypair()
    receipt = witness_receipt()
    registry = AuthorityRegistry({
        "test-key": AuthorityRecord(
            "test-key", public_pem, frozenset({"captals"}), "ACTIVE", frozenset({"policy-v1"})
        )
    })
    payload = signed_receipt_payload(
        receipt, signer_key_id="test-key", authority_scope="captals", policy_version="policy-v1"
    )
    signature_b64 = base64.b64encode(private_key.sign(payload)).decode("ascii")

    verified_hash = verify_signed_witness_authority(
        receipt=receipt,
        signature_b64=signature_b64,
        signer_key_id="test-key",
        authority_scope="captals",
        policy_version="policy-v1",
        registry=registry,
        ed25519_verify=verify_ed25519,
    )
    assert verified_hash == receipt["receipt_hash"]


def test_real_ed25519_tampered_authority_payload_blocks():
    private_key, public_pem = keypair()
    receipt = witness_receipt()
    registry = AuthorityRegistry({
        "test-key": AuthorityRecord(
            "test-key", public_pem, frozenset({"captals", "research"}), "ACTIVE", frozenset({"policy-v1"})
        )
    })
    payload = signed_receipt_payload(
        receipt, signer_key_id="test-key", authority_scope="captals", policy_version="policy-v1"
    )
    signature_b64 = base64.b64encode(private_key.sign(payload)).decode("ascii")

    with pytest.raises(ValidationError, match="signature verification failed"):
        verify_signed_witness_authority(
            receipt=receipt,
            signature_b64=signature_b64,
            signer_key_id="test-key",
            authority_scope="research",
            policy_version="policy-v1",
            registry=registry,
            ed25519_verify=verify_ed25519,
        )


def test_real_ed25519_wrong_key_blocks():
    private_key, _ = keypair()
    _, wrong_public_pem = keypair()
    receipt = witness_receipt()
    registry = AuthorityRegistry({
        "test-key": AuthorityRecord(
            "test-key", wrong_public_pem, frozenset({"captals"}), "ACTIVE", frozenset({"policy-v1"})
        )
    })
    payload = signed_receipt_payload(
        receipt, signer_key_id="test-key", authority_scope="captals", policy_version="policy-v1"
    )
    signature_b64 = base64.b64encode(private_key.sign(payload)).decode("ascii")

    with pytest.raises(ValidationError, match="signature verification failed"):
        verify_signed_witness_authority(
            receipt=receipt,
            signature_b64=signature_b64,
            signer_key_id="test-key",
            authority_scope="captals",
            policy_version="policy-v1",
            registry=registry,
            ed25519_verify=verify_ed25519,
        )
