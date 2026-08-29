from __future__ import annotations

from dataclasses import dataclass
import base64
from hashlib import sha256
import json
from typing import Callable, Iterable

from .authority import AuthorityRecord, AuthorityRegistry
from .valuechain import ValidationError

_ALLOWED = {"GRANT", "ROTATE", "SUSPEND", "RESUME", "REVOKE"}
_GENESIS = "GENESIS"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class AuthorityEvent:
    sequence: int
    event_type: str
    effective_at_unix: int
    signer_key_id: str
    public_key_pem: str
    scopes: frozenset[str]
    policy_versions: frozenset[str]
    previous_event_hash: str
    authorizer_key_id: str
    signature_b64: str

    def body(self) -> dict[str, object]:
        return {
            "authorizer_key_id": self.authorizer_key_id,
            "effective_at_unix": self.effective_at_unix,
            "event_type": self.event_type,
            "policy_versions": sorted(self.policy_versions),
            "previous_event_hash": self.previous_event_hash,
            "public_key_pem": self.public_key_pem,
            "schema_version": "matverse.authority-event.v1",
            "scopes": sorted(self.scopes),
            "sequence": self.sequence,
            "signer_key_id": self.signer_key_id,
        }

    def event_hash(self) -> str:
        return _hash(self.body())

    def validate(self) -> None:
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence <= 0:
            raise ValidationError("authority event sequence must be positive")
        if self.event_type not in _ALLOWED:
            raise ValidationError("authority event type is invalid")
        if isinstance(self.effective_at_unix, bool) or not isinstance(self.effective_at_unix, int) or self.effective_at_unix <= 0:
            raise ValidationError("authority event effective_at_unix is invalid")
        if not self.signer_key_id.strip() or not self.authorizer_key_id.strip():
            raise ValidationError("authority event key ids are required")
        if "BEGIN PUBLIC KEY" not in self.public_key_pem:
            raise ValidationError("authority event public key is invalid")
        if not self.scopes or any(not x.strip() for x in self.scopes):
            raise ValidationError("authority event scopes are invalid")
        if self.sequence == 1 and self.previous_event_hash != _GENESIS:
            raise ValidationError("first authority event must reference GENESIS")
        if self.sequence > 1 and (len(self.previous_event_hash) != 64 or any(c not in "0123456789abcdef" for c in self.previous_event_hash)):
            raise ValidationError("authority event previous hash is invalid")
        try:
            signature = base64.b64decode(self.signature_b64, validate=True)
        except Exception as exc:
            raise ValidationError("authority event signature is invalid base64") from exc
        if len(signature) != 64:
            raise ValidationError("authority event Ed25519 signature must be 64 bytes")


def verify_authority_history(
    events: Iterable[AuthorityEvent], *,
    root_key_id: str, root_public_key_pem: str,
    ed25519_verify: Callable[[str, bytes, bytes], bool],
) -> list[AuthorityEvent]:
    ordered = list(events)
    if not ordered:
        raise ValidationError("authority history is empty")
    known_keys = {root_key_id: root_public_key_pem}
    states: dict[str, str] = {}
    previous_hash = _GENESIS
    previous_time = 0
    seen_hashes: set[str] = set()

    for index, event in enumerate(ordered, 1):
        event.validate()
        if event.sequence != index:
            raise ValidationError("authority history sequence is not contiguous")
        if event.previous_event_hash != previous_hash:
            raise ValidationError("authority history previous hash mismatch")
        if event.effective_at_unix < previous_time:
            raise ValidationError("authority history time is not monotonic")
        authorizer_pem = known_keys.get(event.authorizer_key_id)
        if authorizer_pem is None or (event.authorizer_key_id != root_key_id and states.get(event.authorizer_key_id) != "ACTIVE"):
            raise ValidationError("authority event authorizer is not active")
        try:
            signature = base64.b64decode(event.signature_b64, validate=True)
            ok = ed25519_verify(authorizer_pem, _canonical(event.body()), signature)
        except Exception as exc:
            raise ValidationError("authority event signature verification failed closed") from exc
        if ok is not True:
            raise ValidationError("authority event signature verification failed")

        current = states.get(event.signer_key_id)
        if event.event_type == "GRANT":
            if current is not None:
                raise ValidationError("authority signer already exists")
            states[event.signer_key_id] = "ACTIVE"
            known_keys[event.signer_key_id] = event.public_key_pem
        elif event.event_type == "ROTATE":
            if current != "ACTIVE":
                raise ValidationError("only active authority can rotate")
            known_keys[event.signer_key_id] = event.public_key_pem
        elif event.event_type == "SUSPEND":
            if current != "ACTIVE": raise ValidationError("only active authority can suspend")
            states[event.signer_key_id] = "SUSPENDED"
        elif event.event_type == "RESUME":
            if current != "SUSPENDED": raise ValidationError("only suspended authority can resume")
            states[event.signer_key_id] = "ACTIVE"
        elif event.event_type == "REVOKE":
            if current not in {"ACTIVE", "SUSPENDED"}: raise ValidationError("authority cannot be revoked from current state")
            states[event.signer_key_id] = "REVOKED"

        digest = event.event_hash()
        if digest in seen_hashes: raise ValidationError("duplicate authority event hash")
        seen_hashes.add(digest)
        previous_hash, previous_time = digest, event.effective_at_unix
    return ordered


def registry_at(
    events: Iterable[AuthorityEvent], *, at_unix: int,
    root_key_id: str, root_public_key_pem: str,
    ed25519_verify: Callable[[str, bytes, bytes], bool],
) -> AuthorityRegistry:
    if isinstance(at_unix, bool) or not isinstance(at_unix, int) or at_unix <= 0:
        raise ValidationError("authority replay time is invalid")
    verified = verify_authority_history(events, root_key_id=root_key_id, root_public_key_pem=root_public_key_pem, ed25519_verify=ed25519_verify)
    records: dict[str, AuthorityRecord] = {}
    for event in verified:
        if event.effective_at_unix > at_unix:
            break
        old = records.get(event.signer_key_id)
        if event.event_type == "GRANT":
            records[event.signer_key_id] = AuthorityRecord(event.signer_key_id, event.public_key_pem, event.scopes, "ACTIVE", event.policy_versions, event.effective_at_unix, None)
        elif event.event_type == "ROTATE" and old:
            records[event.signer_key_id] = AuthorityRecord(old.signer_key_id, event.public_key_pem, event.scopes, old.status, event.policy_versions, old.valid_from_unix, old.valid_until_unix)
        elif event.event_type in {"SUSPEND", "RESUME", "REVOKE"} and old:
            status = {"SUSPEND":"SUSPENDED", "RESUME":"ACTIVE", "REVOKE":"REVOKED"}[event.event_type]
            records[event.signer_key_id] = AuthorityRecord(old.signer_key_id, old.public_key_pem, old.scopes, status, old.policy_versions, old.valid_from_unix, event.effective_at_unix if status == "REVOKED" else old.valid_until_unix)
    return AuthorityRegistry(records)
