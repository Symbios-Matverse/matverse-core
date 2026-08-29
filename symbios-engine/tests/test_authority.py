import base64
from hashlib import sha256
import json

import pytest

from core.authority import AuthorityRecord, AuthorityRegistry, signed_receipt_payload, verify_signed_witness_authority
from core.valuechain import ValidationError

PEM = "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEActbhiqZidrvYUCU4QWwLsrFl0K8Nzyq/7BL8qwnrz9k=\n-----END PUBLIC KEY-----\n"


def receipt():
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


def registry(status="ACTIVE", scopes=frozenset({"captals"}), policies=frozenset({"policy-v1"})):
    rec = AuthorityRecord("root-v1", PEM, scopes, status, policies)
    return AuthorityRegistry({"root-v1": rec})


def fake_signature():
    return base64.b64encode(b"s" * 64).decode()


def ok_verify(public_key_pem, payload, signature):
    return public_key_pem == PEM and len(payload) > 0 and signature == b"s" * 64


def test_authorized_signed_receipt_passes():
    verified = verify_signed_witness_authority(
        receipt=receipt(), signature_b64=fake_signature(), signer_key_id="root-v1",
        authority_scope="captals", policy_version="policy-v1", registry=registry(), ed25519_verify=ok_verify,
    )
    assert len(verified) == 64


def test_unknown_signer_blocks():
    with pytest.raises(ValidationError, match="unknown signer"):
        verify_signed_witness_authority(receipt=receipt(), signature_b64=fake_signature(), signer_key_id="other", authority_scope="captals", policy_version="policy-v1", registry=registry(), ed25519_verify=ok_verify)


def test_revoked_signer_blocks():
    with pytest.raises(ValidationError, match="revoked"):
        verify_signed_witness_authority(receipt=receipt(), signature_b64=fake_signature(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v1", registry=registry(status="REVOKED"), ed25519_verify=ok_verify)


def test_insufficient_scope_blocks():
    with pytest.raises(ValidationError, match="scope"):
        verify_signed_witness_authority(receipt=receipt(), signature_b64=fake_signature(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v1", registry=registry(scopes=frozenset({"research"})), ed25519_verify=ok_verify)


def test_incompatible_policy_blocks():
    with pytest.raises(ValidationError, match="policy"):
        verify_signed_witness_authority(receipt=receipt(), signature_b64=fake_signature(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v2", registry=registry(), ed25519_verify=ok_verify)


def test_invalid_signature_blocks():
    with pytest.raises(ValidationError, match="signature verification failed"):
        verify_signed_witness_authority(receipt=receipt(), signature_b64=fake_signature(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v1", registry=registry(), ed25519_verify=lambda *_: False)


def test_crypto_exception_fails_closed():
    def explode(*_):
        raise RuntimeError("crypto unavailable")
    with pytest.raises(ValidationError, match="failed closed"):
        verify_signed_witness_authority(receipt=receipt(), signature_b64=fake_signature(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v1", registry=registry(), ed25519_verify=explode)


def test_tampered_receipt_blocks_before_signature():
    value = receipt()
    value["status"] = "HOLD"
    with pytest.raises(ValidationError, match="hash mismatch"):
        verify_signed_witness_authority(receipt=value, signature_b64=fake_signature(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v1", registry=registry(), ed25519_verify=ok_verify)


def test_signature_payload_binds_scope_policy_signer_and_receipt():
    a = signed_receipt_payload(receipt(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v1")
    b = signed_receipt_payload(receipt(), signer_key_id="root-v1", authority_scope="research", policy_version="policy-v1")
    assert a != b
