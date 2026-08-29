from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Collection, Mapping

from .valuechain import Decision, MemBit, MemNanoBit, ValidationError


_HEX = set("0123456789abcdef")
_ALLOWED_RECEIPT_STATUSES = {"PASS", "HOLD", "BLOCK", "DRY_RUN"}


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value.lower()) <= _HEX


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValidationError("receipt must be canonical JSON-compatible") from exc


def _sha256_hex(value: Any) -> str:
    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = _canonical_json(value).encode("utf-8")
    return sha256(payload).hexdigest()


def verify_witness_receipt(receipt: Mapping[str, Any]) -> str:
    """Verify the Scientific Witness v0.1 Receipt contract locally.

    This intentionally mirrors the observable receipt verification contract from
    MatVerse-py/matverse-u-kernel without importing that repository at runtime.
    The returned value is the verified receipt hash.
    """

    if not isinstance(receipt, Mapping):
        raise ValidationError("receipt must be a mapping")

    kind = receipt.get("kind")
    status = receipt.get("status")
    subject_hash = receipt.get("subject_hash")
    issued_at = receipt.get("issued_at_unix")
    details = receipt.get("details")
    supplied_hash = receipt.get("receipt_hash")

    if not isinstance(kind, str) or not kind.strip():
        raise ValidationError("receipt kind is invalid")
    if status not in _ALLOWED_RECEIPT_STATUSES:
        raise ValidationError("receipt status is invalid")
    if not _is_sha256(subject_hash):
        raise ValidationError("receipt subject_hash is invalid")
    if isinstance(issued_at, bool) or not isinstance(issued_at, int) or issued_at <= 0:
        raise ValidationError("receipt issued_at_unix is invalid")
    if not isinstance(details, Mapping):
        raise ValidationError("receipt details must be a mapping")
    if not _is_sha256(supplied_hash):
        raise ValidationError("receipt_hash is invalid")

    body = dict(receipt)
    body.pop("receipt_hash", None)
    computed = _sha256_hex(body)
    if supplied_hash.lower() != computed:
        raise ValidationError("receipt hash mismatch")
    return computed


def materialize_mem_bit_from_witness(
    *,
    mem_nano_bit: MemNanoBit,
    receipt: Mapping[str, Any],
    policy_version: str,
    signer_key_id: str,
    authority_scope: str,
    claim_type: str = "witness_commitment",
    accepted_kinds: Collection[str] | None = None,
    required_subject_hash: str | None = None,
) -> MemBit:
    """Materialize a MemBit only from a verified PASS/HOLD witness receipt.

    BLOCK and DRY_RUN receipts are never commitments. Authority identifiers are
    pinned here but cryptographic signature verification remains an external
    authority/registry responsibility until that contract is integrated.
    """

    receipt_hash = verify_witness_receipt(receipt)
    kind = str(receipt["kind"])
    status = str(receipt["status"])
    subject_hash = str(receipt["subject_hash"]).lower()

    if accepted_kinds is not None and kind not in set(accepted_kinds):
        raise ValidationError("receipt kind is not accepted by this adapter")
    if required_subject_hash is not None:
        if not _is_sha256(required_subject_hash) or subject_hash != required_subject_hash.lower():
            raise ValidationError("receipt subject does not match required subject")
    if status in {"BLOCK", "DRY_RUN"}:
        raise ValidationError(f"receipt status {status} cannot materialize a MemBit")

    decision = Decision.PASS if status == "PASS" else Decision.HOLD
    mem_bit = MemBit(
        mem_nano_bit=mem_nano_bit,
        decision_gate=decision,
        evidence_hash=receipt_hash,
        policy_version=policy_version,
        signer_key_id=signer_key_id,
        authority_scope=authority_scope,
        claim_type=claim_type,
    )
    mem_bit.validate()
    return mem_bit
