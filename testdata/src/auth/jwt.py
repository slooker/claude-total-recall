"""
src/auth/jwt.py

JWT token creation and validation.
Tokens expire after 24h. Refresh tokens expire after 30 days.

The refresh token flow was added in session 3 (2026-04-22) after being
left incomplete in session 2. The original implementation only handled
access tokens.
"""

import os
import time
import hmac
import hashlib
import base64
import json
from typing import Optional

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
ACCESS_TOKEN_TTL = 60 * 60 * 24        # 24 hours
REFRESH_TOKEN_TTL = 60 * 60 * 24 * 30  # 30 days
ALGORITHM = "HS256"


class TokenExpiredError(Exception):
    pass


class TokenInvalidError(Exception):
    pass


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    return base64.urlsafe_b64decode(data + "=" * padding)


def _sign(header_b64: str, payload_b64: str, secret: str) -> str:
    message = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    return _b64_encode(sig)


def create_access_token(user_id: str, extra_claims: Optional[dict] = None) -> str:
    """Creates a signed JWT access token valid for 24 hours."""
    now = int(time.time())
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
        "type": "access",
        **(extra_claims or {}),
    }
    h = _b64_encode(json.dumps(header).encode())
    p = _b64_encode(json.dumps(payload).encode())
    sig = _sign(h, p, JWT_SECRET)
    return f"{h}.{p}.{sig}"


def create_refresh_token(user_id: str) -> str:
    """
    Creates a signed JWT refresh token valid for 30 days.
    Refresh tokens have a 'type': 'refresh' claim so they can't be
    used as access tokens.
    """
    now = int(time.time())
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + REFRESH_TOKEN_TTL,
        "type": "refresh",
    }
    h = _b64_encode(json.dumps(header).encode())
    p = _b64_encode(json.dumps(payload).encode())
    sig = _sign(h, p, JWT_SECRET)
    return f"{h}.{p}.{sig}"


def decode_token(token: str, expected_type: str = "access") -> dict:
    """
    Decodes and validates a JWT token.
    Raises TokenExpiredError if expired, TokenInvalidError if tampered.
    """
    try:
        h, p, sig = token.split(".")
    except ValueError:
        raise TokenInvalidError("Malformed token — expected 3 segments")

    expected_sig = _sign(h, p, JWT_SECRET)
    if not hmac.compare_digest(expected_sig, sig):
        raise TokenInvalidError("Signature verification failed")

    payload = json.loads(_b64_decode(p))

    if payload.get("exp", 0) < int(time.time()):
        raise TokenExpiredError("Token has expired")

    if payload.get("type") != expected_type:
        raise TokenInvalidError(
            f"Wrong token type: expected '{expected_type}', got '{payload.get('type')}'"
        )

    return payload


def refresh_access_token(refresh_token: str) -> tuple[str, str]:
    """
    Validates a refresh token and issues a new access + refresh token pair.
    Old refresh token is invalidated implicitly (single-use via DB — see
    auth/refresh_store.py for the rotation logic).

    Returns (new_access_token, new_refresh_token).
    """
    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = payload["sub"]
    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)
    return new_access, new_refresh
