"""The tool's RSA signing key. Generated once, kept on the data volume."""

from __future__ import annotations

import base64
import hashlib
import os
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ..config import get_settings


def _b64url(n: int, length: int) -> str:
    return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()


@lru_cache
def private_key() -> rsa.RSAPrivateKey:
    path = get_settings().lti_key_path
    if os.path.exists(path):
        with open(path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
            assert isinstance(key, rsa.RSAPrivateKey)
            return key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    with open(path, "wb") as f:
        f.write(pem)
    os.chmod(path, 0o600)
    return key


def private_pem() -> bytes:
    return private_key().private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())


def public_pem() -> bytes:
    return private_key().public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


@lru_cache
def kid() -> str:
    der = private_key().public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return hashlib.sha256(der).hexdigest()[:16]


def jwks() -> dict:
    numbers = private_key().public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": kid(),
                "n": _b64url(numbers.n, (numbers.n.bit_length() + 7) // 8),
                "e": _b64url(numbers.e, 3),
            }
        ]
    }
