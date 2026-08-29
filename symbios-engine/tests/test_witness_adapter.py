from hashlib import sha256
import json

import pytest

from core.valuechain import Decision, MNB, MemNanoBit, ValidationError
from core.witness_adapter import materialize_mem_bit_from_witness, verify_witness_receipt


def canonical_hash(body):
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def receipt(status="PASS", kind="witness.release", subject_hash=None):
    body = {
        "kind": kind,
        "status": status,
        "subject_hash": subject_hash or ("a" * 64),
        "issued_at_unix": 1787960000,
        "details": {"source": "matverse-u-kernel", "mode": "fail_closed"},
    }
    return {**body, "receipt_hash": canonical_hash(body)}


def nano():
    mnb = MNB("e-witness", "scientific_witness", "b" * 64, "c" * 64, "2026-08-29T00:00:00Z")
    return MemNanoBit(mnb, "continuity-witness")


def materialize(r, **kwargs):
    return materialize_mem_bit_from_witness(
        mem_nano_bit=nano(),
        receipt=r,
        policy_version="witness-policy-v0.1",
        signer_key_id="kernel-key-v1",
        authority_scope="scientific-witness",
        accepted_kinds={"witness.release"},
        required_subject_hash="a" * 64,
        **kwargs,
    )


def test_valid_pass_receipt_materializes_pass_membit():
    r = receipt()
    mem = materialize(r)
    assert mem.decision_gate is Decision.PASS
    assert mem.evidence_hash == r["receipt_hash"]
    assert mem.claim_type == "witness_commitment"


def test_valid_hold_receipt_materializes_hold_membit():
    mem = materialize(receipt(status="HOLD"))
    assert mem.decision_gate is Decision.HOLD


def test_tampered_receipt_is_blocked():
    r = receipt()
    r["details"]["mode"] = "permissive"
    with pytest.raises(ValidationError, match="hash mismatch"):
        materialize(r)


@pytest.mark.parametrize("status", ["BLOCK", "DRY_RUN"])
def test_non_commitment_statuses_cannot_materialize(status):
    with pytest.raises(ValidationError, match="cannot materialize"):
        materialize(receipt(status=status))


def test_unrecognized_status_is_blocked_before_materialization():
    r = receipt(status="PASS")
    r["status"] = "EXECUTE"
    body = dict(r)
    body.pop("receipt_hash")
    r["receipt_hash"] = canonical_hash(body)
    with pytest.raises(ValidationError, match="status is invalid"):
        materialize(r)


def test_wrong_kind_is_blocked():
    with pytest.raises(ValidationError, match="kind is not accepted"):
        materialize(receipt(kind="external.github.publish"))


def test_wrong_subject_is_blocked():
    with pytest.raises(ValidationError, match="subject does not match"):
        materialize(receipt(subject_hash="d" * 64))


def test_receipt_hash_verifier_matches_witness_contract():
    r = receipt()
    assert verify_witness_receipt(r) == r["receipt_hash"]


def test_boolean_timestamp_is_rejected():
    r = receipt()
    r["issued_at_unix"] = True
    body = dict(r)
    body.pop("receipt_hash")
    r["receipt_hash"] = canonical_hash(body)
    with pytest.raises(ValidationError, match="issued_at_unix"):
        verify_witness_receipt(r)


def test_non_mapping_details_is_rejected():
    r = receipt()
    r["details"] = []
    body = dict(r)
    body.pop("receipt_hash")
    r["receipt_hash"] = canonical_hash(body)
    with pytest.raises(ValidationError, match="details"):
        verify_witness_receipt(r)
