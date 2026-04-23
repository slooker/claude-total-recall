"""
tests/test_stripe_webhook.py

Tests for the Stripe webhook handler (src/webhooks/stripe.py).
Covers signature verification, event routing, and tier updates.
"""

import hashlib
import hmac
import json
import time
import pytest
from unittest.mock import patch, MagicMock

from webhooks.stripe import (
    handle_webhook,
    verify_signature,
    WebhookVerificationError,
    WebhookHandlerError,
)

TEST_SECRET = "whsec_test_secret_key_for_unit_tests"


def make_signature(payload: bytes, secret: str, timestamp: int = None) -> str:
    ts = timestamp or int(time.time())
    signed = f"{ts}.".encode() + payload
    sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def make_event(event_type: str, data: dict) -> bytes:
    return json.dumps({"type": event_type, "data": {"object": data}}).encode()


class TestSignatureVerification:
    def test_valid_signature_passes(self):
        payload = b'{"type": "test"}'
        sig = make_signature(payload, TEST_SECRET)
        verify_signature(payload, sig, TEST_SECRET)  # should not raise

    def test_wrong_secret_raises(self):
        payload = b'{"type": "test"}'
        sig = make_signature(payload, TEST_SECRET)
        with pytest.raises(WebhookVerificationError, match="Signature mismatch"):
            verify_signature(payload, sig, "wrong_secret")

    def test_expired_timestamp_raises(self):
        payload = b'{"type": "test"}'
        old_ts = int(time.time()) - 600  # 10 minutes ago
        sig = make_signature(payload, TEST_SECRET, timestamp=old_ts)
        with pytest.raises(WebhookVerificationError, match="timestamp too old"):
            verify_signature(payload, sig, TEST_SECRET)

    def test_malformed_header_raises(self):
        with pytest.raises(WebhookVerificationError, match="Malformed"):
            verify_signature(b"payload", "not-a-valid-header", TEST_SECRET)

    def test_missing_secret_raises(self):
        with pytest.raises(WebhookVerificationError, match="not configured"):
            verify_signature(b"payload", "t=1,v1=abc", "")


class TestPaymentIntentSucceeded:
    @patch("webhooks.stripe.set_user_tier")
    @patch("webhooks.stripe.invalidate_feature_cache")
    @patch("webhooks.stripe.STRIPE_WEBHOOK_SECRET", TEST_SECRET)
    def test_upgrades_user_to_pro(self, mock_cache, mock_set_tier):
        payload = make_event("payment_intent.succeeded", {
            "customer": "cus_123",
            "metadata": {"user_id": "user_abc", "subscription_tier": "pro"},
        })
        sig = make_signature(payload, TEST_SECRET)
        result = handle_webhook(payload, sig)
        assert result == {"status": "ok"}
        mock_set_tier.assert_called_once_with("user_abc", "pro")
        mock_cache.assert_called_once_with("user_abc")

    @patch("webhooks.stripe.set_user_tier")
    @patch("webhooks.stripe.STRIPE_WEBHOOK_SECRET", TEST_SECRET)
    def test_no_user_id_does_not_call_set_tier(self, mock_set_tier):
        payload = make_event("payment_intent.succeeded", {
            "customer": "cus_123",
            "metadata": {},
        })
        sig = make_signature(payload, TEST_SECRET)
        handle_webhook(payload, sig)
        mock_set_tier.assert_not_called()


class TestSubscriptionDeleted:
    @patch("webhooks.stripe.set_user_tier")
    @patch("webhooks.stripe.invalidate_feature_cache")
    @patch("webhooks.stripe.STRIPE_WEBHOOK_SECRET", TEST_SECRET)
    def test_downgrades_user_to_free(self, mock_cache, mock_set_tier):
        payload = make_event("customer.subscription.deleted", {
            "customer": "cus_123",
            "metadata": {"user_id": "user_abc"},
        })
        sig = make_signature(payload, TEST_SECRET)
        handle_webhook(payload, sig)
        mock_set_tier.assert_called_once_with("user_abc", "free")
        mock_cache.assert_called_once_with("user_abc")


class TestUnhandledEvent:
    @patch("webhooks.stripe.STRIPE_WEBHOOK_SECRET", TEST_SECRET)
    def test_unknown_event_returns_ok(self):
        payload = make_event("some.unknown.event", {})
        sig = make_signature(payload, TEST_SECRET)
        result = handle_webhook(payload, sig)
        assert result == {"status": "ok"}
