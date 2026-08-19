from __future__ import annotations

import json
import os
from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

KDF_TIME_COST = 3
KDF_MEMORY_COST = 65536
KDF_PARALLELISM = 2
KEY_LEN = 32


def derive_key(password: str, salt: bytes) -> bytes:
    if not password:
        raise ValueError("Password cannot be empty.")
    return hash_secret_raw(
        password.encode("utf-8"),
        salt,
        time_cost=KDF_TIME_COST,
        memory_cost=KDF_MEMORY_COST,
        parallelism=KDF_PARALLELISM,
        hash_len=KEY_LEN,
        type=Type.ID,
    )


def make_verifier(key: bytes) -> bytes:
    """Verifier used by Quarries v0.3.x."""
    nonce = b"\0" * 12
    return ChaCha20Poly1305(key).encrypt(
        nonce, b"quarries-password-verifier-v3", b"quarries-verifier"
    )


def make_legacy_verifier(key: bytes) -> bytes:
    """Verifier used by Quarries v0.1.x and v0.2.x."""
    nonce = b"\0" * 12
    return ChaCha20Poly1305(key).encrypt(
        nonce, b"quarries-password-verifier", b"quarries"
    )


def password_matches(key: bytes, stored_verifier: bytes) -> bool:
    """Accept all verifier formats released by Quarries so far."""
    return stored_verifier in {
        make_verifier(key),
        make_legacy_verifier(key),
    }


def encrypt_bytes(key: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    nonce = os.urandom(12)
    return nonce + ChaCha20Poly1305(key).encrypt(nonce, plaintext, aad)


def decrypt_bytes(key: bytes, packed: bytes, aad: bytes = b"") -> bytes:
    if len(packed) < 29:
        raise ValueError("Encrypted field is malformed.")
    nonce = packed[:12]
    return ChaCha20Poly1305(key).decrypt(nonce, packed[12:], aad)


def encrypt_text(key: bytes, text: str, aad: bytes = b"") -> bytes:
    return encrypt_bytes(key, text.encode("utf-8"), aad)


def decrypt_text(key: bytes, packed: bytes, aad: bytes = b"") -> str:
    return decrypt_bytes(key, packed, aad).decode("utf-8")


def encrypt_json(key: bytes, value, aad: bytes = b"") -> bytes:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return encrypt_bytes(key, raw, aad)


def decrypt_json(key: bytes, packed: bytes, aad: bytes = b""):
    return json.loads(decrypt_bytes(key, packed, aad).decode("utf-8"))
