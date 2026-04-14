"""Fernet-based symmetric encryption for analysis data stored in the DB.

Raw PDFs are NEVER stored — only the extracted analysis JSON is stored,
and it is encrypted at rest with a key derived from the application SECRET_KEY.
"""
import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

_DEFAULT_KEY = "change-me-in-production-use-a-long-random-string"


def _build_fernet() -> Fernet:
    secret = os.getenv("SECRET_KEY", "")
    if not secret:
        logger.warning(
            "SECRET_KEY environment variable is not set. "
            "Using an insecure default — set SECRET_KEY before deploying to production."
        )
        secret = _DEFAULT_KEY
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
