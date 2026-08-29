from __future__ import annotations

from dataclasses import dataclass
import base64
from typing import Any, Callable, Mapping

from .valuechain import ValidationError
from .witness_adapter import _canonical_json, verify_witness_receipt


@dataclass(frozen=True)
class AuthorityRecord:
    signer_key_id: str
    public_key_pem: str
    scopes: frozenset[str]
    status: str = "ACTIVE"
    policy_versions: frozenset[str] = frozenset()

    def validate(self) -> None:
        if not self.signer_key_id.strip():
            raise ValidationError("signer_key_id is required")
        if "BEGIN PUBLIC KEY" not in self.public_key_pem:
            raise ValidationError("public_key_pem is invalid")
        if not self.scopes or any(not isinstance(s, str) or not s.strip() for s in self.scopes):
            raise ValidationError("authority scopes are invalid")
        if self.status not in {"ACTIVE", "REVOKED", "SUSPENDED"}:
            raise ValidationError("authority status is invalid")
        if any(not isinstance(p, str) or not p.strip() for p in self.policy_versions):
            raise ValidationError("policy_versions are invalid")


class AuthorityRegistry:
    def __init__(self, records: Mapping[str, AuthorityRecord]):
        self._records = dict(records)
        for key_id, record in self._records.items():
            record.validate()
            if key_id != record.signer_key_id:
                raise ValidationError("registry key does not match signer_key_id")

    def authorize(self, *, signer_key_id: str, scope: str, policy_version: str) -> AuthorityRecord:
        record = self._records.get(signer_key_id)
        if record is None:
            raise ValidationError("unknown signer")
        if record.status != "ACTIVE":
            raise ValidationError(f"signer is {record.status.lower()}")
        if scope not in record.scopes:
            raise ValidationError("authority scope is not granted")
        if record.policy_versions and policy_version not in record.policy_versions:
            raise ValidationError("policy version is not authorized")
        return record


def signed_receipt_payload(receipt: Mapping[str, Any], *, signer_key_id: str, authority_scope: str, policy_version: str) -> bytes:
    receipt_hash = verify_witness_receipt(receipt)
    return _canonical_json({
        "authority_scope": authority_scope,
        "policy_version": policy_version,
        "receipt_hash": receipt_hash,
        "signer_key_id": signer_key_id,
        "schema_version": "matverse.signed-witness-receipt.v1",
    }).encode("utf-8")


def verify_signed_witness_authority(
    *,
    receipt: Mapping[str, Any],
    signature_b64: str,
    signer_key_id: str,
    authority_scope: str,
    policy_version: str,
    registry: AuthorityRegistry,
    ed25519_verify: Callable[[str, bytes, bytes], bool],
) -> str:
    """Fail-closed authority verification around an already verified witness receipt.

    Crypto is injected so the core remains decoupled from a specific crypto package;
    production callers must supply a real Ed25519 verifier. Returning False or raising
    from the verifier blocks materialization.
    """
    record = registry.authorize(signer_key_id=signer_key_id, scope=authority_scope, policy_version=policy_version)
    payload = signed_receipt_payload(receipt, signer_key_id=signer_key_id, authority_scope=authority_scope, policy_version=policy_version)
    if not isinstance(signature_b64, str) or not signature_b64.strip():
        raise ValidationError("signature is required")
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except Exception as exc:
        raise ValidationError("signature is not valid base64") from exc
    if len(signature) != 64:
        raise ValidationError("Ed25519 signature must be 64 bytes")
    try:
        verified = ed25519_verify(record.public_key_pem, payload, signature)
    except Exception as exc:
        raise ValidationError("Ed25519 verification failed closed") from exc
    if verified is not True:
        raise ValidationError("Ed25519 signature verification failed")
    return verify_witness_receipt(receipt)
