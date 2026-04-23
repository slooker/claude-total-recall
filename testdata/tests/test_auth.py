"""
tests/test_auth.py

Tests for JWT token creation, validation, and the refresh token flow.
The refresh token flow was the focus of session 3 (2026-04-22).
"""

import time
import pytest
from unittest.mock import patch

from auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    refresh_access_token,
    TokenExpiredError,
    TokenInvalidError,
)


class TestAccessTokens:
    def test_create_and_decode(self):
        token = create_access_token("user_123")
        payload = decode_token(token)
        assert payload["sub"] == "user_123"
        assert payload["type"] == "access"

    def test_extra_claims_included(self):
        token = create_access_token("user_123", extra_claims={"role": "admin"})
        payload = decode_token(token)
        assert payload["role"] == "admin"

    def test_expired_token_raises(self):
        token = create_access_token("user_123")
        with patch("auth.jwt.time") as mock_time:
            mock_time.time.return_value = time.time() + 90000  # 25h later
            with pytest.raises(TokenExpiredError):
                decode_token(token)

    def test_tampered_token_raises(self):
        token = create_access_token("user_123")
        parts = token.split(".")
        parts[1] = parts[1][:-2] + "XX"  # corrupt payload
        with pytest.raises(TokenInvalidError, match="Signature"):
            decode_token(".".join(parts))

    def test_refresh_token_rejected_as_access(self):
        refresh = create_refresh_token("user_123")
        with pytest.raises(TokenInvalidError, match="Wrong token type"):
            decode_token(refresh, expected_type="access")


class TestRefreshTokenFlow:
    def test_refresh_issues_new_token_pair(self):
        refresh = create_refresh_token("user_456")
        new_access, new_refresh = refresh_access_token(refresh)

        access_payload = decode_token(new_access, expected_type="access")
        refresh_payload = decode_token(new_refresh, expected_type="refresh")

        assert access_payload["sub"] == "user_456"
        assert refresh_payload["sub"] == "user_456"
        assert new_refresh != refresh  # new token issued

    def test_expired_refresh_token_raises(self):
        refresh = create_refresh_token("user_456")
        with patch("auth.jwt.time") as mock_time:
            mock_time.time.return_value = time.time() + (31 * 24 * 3600)
            with pytest.raises(TokenExpiredError):
                refresh_access_token(refresh)

    def test_access_token_rejected_as_refresh(self):
        access = create_access_token("user_456")
        with pytest.raises(TokenInvalidError, match="Wrong token type"):
            refresh_access_token(access)
