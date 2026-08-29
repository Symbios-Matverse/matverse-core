from __future__ import annotations


def verify_ed25519(public_key_pem: str, payload: bytes, signature: bytes) -> bool:
    """Verify an Ed25519 signature using the same cryptography stack as U-Kernel."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as exc:
        raise RuntimeError("cryptography package is required for Ed25519 verification") from exc

    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    if not isinstance(public_key, ed25519.Ed25519PublicKey):
        raise ValueError("public key is not Ed25519")
    try:
        public_key.verify(signature, payload)
    except InvalidSignature:
        return False
    return True
