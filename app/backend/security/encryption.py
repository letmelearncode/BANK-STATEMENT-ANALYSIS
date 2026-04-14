"""Fernet-based symmetric encryption for analysis data stored in the DB.

Raw PDFs are NEVER stored — only the extracted analysis JSON is stored,
and it is encrypted at rest with a key derived from the application SECRET_KEY.
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet


def _build_fernet() -> Fernet:
    secret = os.getenv("SECRET_KEY", "")
    if not secret:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Set a strong random SECRET_KEY before starting the application."
        )
    if len(secret) < 32:
        raise RuntimeError(
            "SECRET_KEY is too short (minimum 32 characters). "
            "Use a cryptographically random value, e.g.: openssl rand -hex 32"
        )
    # Derive a 32-byte key from the secret using SHA-256 then base64url-encode it.
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


_fernet = _build_fernet()


def encrypt(plaintext: str) -> str:
    """Encrypt a UTF-8 string; returns a base64url token string."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt`; returns the original string."""
    return _fernet.decrypt(token.encode()).decode()
