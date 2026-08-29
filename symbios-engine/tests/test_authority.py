import base64
from hashlib import sha256
import json

import pytest

from core.authority import AuthorityRecord, AuthorityRegistry, signed_receipt_payload, verify_signed_witness_authority
from core.valuechain import ValidationError

PEM = "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEActbhiqZidrvYUCU4QWwLsrFl0K8Nzyq/7BL8qwnrz9k=\n-----END PUBLIC KEY-----\n"
ISSUED = 1787972000


def receipt(issued_at=ISSUED):
    body = {"kind":"scientific_witness","status":"PASS","subject_hash":"a"*64,"issued_at_unix":issued_at,"details":{"source":"u-kernel"}}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["receipt_hash"] = sha256(raw.encode()).hexdigest()
    return body


def registry(status="ACTIVE", scopes=frozenset({"captals"}), policies=frozenset({"policy-v1"}), valid_from=None, valid_until=None):
    rec = AuthorityRecord("root-v1", PEM, scopes, status, policies, valid_from, valid_until)
    return AuthorityRegistry({"root-v1": rec})


def fake_signature(): return base64.b64encode(b"s"*64).decode()
def ok_verify(public_key_pem, payload, signature): return public_key_pem == PEM and len(payload)>0 and signature == b"s"*64


def verify(value=None, reg=None):
    return verify_signed_witness_authority(receipt=receipt() if value is None else value, signature_b64=fake_signature(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v1", registry=registry() if reg is None else reg, ed25519_verify=ok_verify)


def test_authorized_signed_receipt_passes(): assert len(verify()) == 64


def test_authority_validity_window_includes_boundaries():
    assert len(verify(reg=registry(valid_from=ISSUED, valid_until=ISSUED))) == 64


def test_receipt_before_authority_valid_from_blocks():
    with pytest.raises(ValidationError, match="not yet valid"):
        verify(reg=registry(valid_from=ISSUED+1))


def test_receipt_after_authority_valid_until_blocks():
    with pytest.raises(ValidationError, match="expired"):
        verify(reg=registry(valid_until=ISSUED-1))


def test_inverted_authority_window_blocks_registry_creation():
    with pytest.raises(ValidationError, match="inverted"):
        registry(valid_from=ISSUED+1, valid_until=ISSUED)


def test_boolean_validity_timestamp_blocks():
    with pytest.raises(ValidationError, match="valid_from_unix"):
        registry(valid_from=True)


def test_unknown_signer_blocks():
    with pytest.raises(ValidationError, match="unknown signer"):
        verify_signed_witness_authority(receipt=receipt(), signature_b64=fake_signature(), signer_key_id="other", authority_scope="captals", policy_version="policy-v1", registry=registry(), ed25519_verify=ok_verify)


def test_revoked_signer_blocks_even_if_receipt_was_inside_window():
    with pytest.raises(ValidationError, match="revoked"):
        verify(reg=registry(status="REVOKED", valid_from=ISSUED-100, valid_until=ISSUED+100))


def test_suspended_signer_blocks_even_if_receipt_was_inside_window():
    with pytest.raises(ValidationError, match="suspended"):
        verify(reg=registry(status="SUSPENDED", valid_from=ISSUED-100, valid_until=ISSUED+100))


def test_insufficient_scope_blocks():
    with pytest.raises(ValidationError, match="scope"):
        verify(reg=registry(scopes=frozenset({"research"})))


def test_incompatible_policy_blocks():
    with pytest.raises(ValidationError, match="policy"):
        verify_signed_witness_authority(receipt=receipt(), signature_b64=fake_signature(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v2", registry=registry(), ed25519_verify=ok_verify)


def test_invalid_signature_blocks():
    with pytest.raises(ValidationError, match="signature verification failed"):
        verify_signed_witness_authority(receipt=receipt(), signature_b64=fake_signature(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v1", registry=registry(), ed25519_verify=lambda *_: False)


def test_crypto_exception_fails_closed():
    def explode(*_): raise RuntimeError("crypto unavailable")
    with pytest.raises(ValidationError, match="failed closed"):
        verify_signed_witness_authority(receipt=receipt(), signature_b64=fake_signature(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v1", registry=registry(), ed25519_verify=explode)


def test_tampered_receipt_blocks_before_authority_or_signature():
    value=receipt(); value["status"]="HOLD"
    with pytest.raises(ValidationError, match="hash mismatch"): verify(value=value)


def test_signature_payload_binds_scope_policy_signer_and_receipt():
    a=signed_receipt_payload(receipt(), signer_key_id="root-v1", authority_scope="captals", policy_version="policy-v1")
    b=signed_receipt_payload(receipt(), signer_key_id="root-v1", authority_scope="research", policy_version="policy-v1")
    assert a != b
