from __future__ import annotations

from typing import Any, Callable, Collection, Mapping

from .authority import AuthorityRegistry, verify_signed_witness_authority
from .valuechain import MemBit, MemNanoBit, ValidationError
from .witness_adapter import materialize_mem_bit_from_witness


def materialize_mem_bit_from_signed_witness(
    *,
    mem_nano_bit: MemNanoBit,
    receipt: Mapping[str, Any],
    signature_b64: str,
    signer_key_id: str,
    authority_scope: str,
    policy_version: str,
    registry: AuthorityRegistry,
    ed25519_verify: Callable[[str, bytes, bytes], bool],
    claim_type: str = "witness_commitment",
    accepted_kinds: Collection[str] | None = None,
    required_subject_hash: str | None = None,
) -> MemBit:
    """Atomically verify signed authority and materialize the corresponding MemBit.

    This is the governed boundary for signed Scientific Witness receipts. Signature,
    registry status, scope, policy, receipt integrity and materialization parameters
    are evaluated in one call. No MemBit is returned unless every check passes.
    """
    verified_hash = verify_signed_witness_authority(
        receipt=receipt,
        signature_b64=signature_b64,
        signer_key_id=signer_key_id,
        authority_scope=authority_scope,
        policy_version=policy_version,
        registry=registry,
        ed25519_verify=ed25519_verify,
    )

    mem_bit = materialize_mem_bit_from_witness(
        mem_nano_bit=mem_nano_bit,
        receipt=receipt,
        policy_version=policy_version,
        signer_key_id=signer_key_id,
        authority_scope=authority_scope,
        claim_type=claim_type,
        accepted_kinds=accepted_kinds,
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
