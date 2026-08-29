from __future__ import annotations

from typing import Any, Callable, Collection, Iterable, Mapping

from .authority import AuthorityRegistry, verify_signed_witness_authority
from .authority_history import AuthorityEvent, registry_at
from .valuechain import MemBit, MemNanoBit, ValidationError
from .witness_adapter import materialize_mem_bit_from_witness, verify_witness_receipt


def materialize_mem_bit_from_signed_witness(
    *, mem_nano_bit: MemNanoBit, receipt: Mapping[str, Any], signature_b64: str,
    signer_key_id: str, authority_scope: str, policy_version: str,
    registry: AuthorityRegistry, ed25519_verify: Callable[[str, bytes, bytes], bool],
    claim_type: str = "witness_commitment", accepted_kinds: Collection[str] | None = None,
    required_subject_hash: str | None = None,
) -> MemBit:
    """Governed boundary using an explicitly supplied authority registry."""
    verified_hash = verify_signed_witness_authority(
        receipt=receipt, signature_b64=signature_b64, signer_key_id=signer_key_id,
        authority_scope=authority_scope, policy_version=policy_version,
        registry=registry, ed25519_verify=ed25519_verify,
    )
    return _materialize_verified(
        mem_nano_bit=mem_nano_bit, receipt=receipt, verified_hash=verified_hash,
        signer_key_id=signer_key_id, authority_scope=authority_scope,
        policy_version=policy_version, claim_type=claim_type,
        accepted_kinds=accepted_kinds, required_subject_hash=required_subject_hash,
    )


def materialize_mem_bit_from_historical_signed_witness(
    *, mem_nano_bit: MemNanoBit, receipt: Mapping[str, Any], signature_b64: str,
    signer_key_id: str, authority_scope: str, policy_version: str,
    authority_events: Iterable[AuthorityEvent], root_key_id: str,
    root_public_key_pem: str, ed25519_verify: Callable[[str, bytes, bytes], bool],
    claim_type: str = "witness_commitment", accepted_kinds: Collection[str] | None = None,
    required_subject_hash: str | None = None,
) -> MemBit:
    """Replay signed authority history at receipt issuance, then atomically materialize."""
    verify_witness_receipt(receipt)
    issued_at_unix = receipt.get("issued_at_unix")
    if isinstance(issued_at_unix, bool) or not isinstance(issued_at_unix, int) or issued_at_unix <= 0:
        raise ValidationError("receipt issued_at_unix is invalid")
    historical_registry = registry_at(
        authority_events, at_unix=issued_at_unix, root_key_id=root_key_id,
        root_public_key_pem=root_public_key_pem, ed25519_verify=ed25519_verify,
    )
    return materialize_mem_bit_from_signed_witness(
        mem_nano_bit=mem_nano_bit, receipt=receipt, signature_b64=signature_b64,
        signer_key_id=signer_key_id, authority_scope=authority_scope,
        policy_version=policy_version, registry=historical_registry,
        ed25519_verify=ed25519_verify, claim_type=claim_type,
        accepted_kinds=accepted_kinds, required_subject_hash=required_subject_hash,
    )


def _materialize_verified(
    *, mem_nano_bit: MemNanoBit, receipt: Mapping[str, Any], verified_hash: str,
    signer_key_id: str, authority_scope: str, policy_version: str, claim_type: str,
    accepted_kinds: Collection[str] | None, required_subject_hash: str | None,
) -> MemBit:
    mem_bit = materialize_mem_bit_from_witness(
        mem_nano_bit=mem_nano_bit, receipt=receipt, policy_version=policy_version,
        signer_key_id=signer_key_id, authority_scope=authority_scope,
        claim_type=claim_type, accepted_kinds=accepted_kinds,
        required_subject_hash=required_subject_hash,
    )
    if mem_bit.evidence_hash != verified_hash:
        raise ValidationError("authorized witness evidence hash changed during materialization")
    if mem_bit.signer_key_id != signer_key_id:
        raise ValidationError("authorized witness signer changed during materialization")
    if mem_bit.authority_scope != authority_scope:
        raise ValidationError("authorized witness scope changed during materialization")
    if mem_bit.policy_version != policy_version:
        raise ValidationError("authorized witness policy changed during materialization")
    return mem_bit
