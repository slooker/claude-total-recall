"""
src/webhooks/stripe.py

Handles incoming Stripe webhook events. Verifies HMAC signatures,
routes events to the appropriate handler, and updates user subscription
tiers in the database.
"""

import hashlib
import hmac
import json
import os
import time
from typing import Any

from billing.tiers import TIER_FREE, TIER_PRO, TIER_ENTERPRISE, set_user_tier
from billing.features import invalidate_feature_cache

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
SIGNATURE_TOLERANCE_SECONDS = 300  # 5 minutes


class WebhookVerificationError(Exception):
    pass


class WebhookHandlerError(Exception):
    pass


def verify_signature(payload: bytes, sig_header: str, secret: str) -> None:
    """
    Verify the Stripe webhook signature using HMAC-SHA256.
    Raises WebhookVerificationError if invalid or expired.
    """
    if not secret:
        raise WebhookVerificationError("STRIPE_WEBHOOK_SECRET not configured")

    try:
        parts = dict(item.split("=", 1) for item in sig_header.split(","))
        timestamp = int(parts["t"])
        signatures = [v for k, v in parts.items() if k == "v1"]
    except (KeyError, ValueError) as e:
        raise WebhookVerificationError(f"Malformed signature header: {e}")

    # Check timestamp to prevent replay attacks
    if abs(time.time() - timestamp) > SIGNATURE_TOLERANCE_SECONDS:
        raise WebhookVerificationError("Webhook timestamp too old — possible replay attack")

    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()

    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise WebhookVerificationError("Signature mismatch")


def handle_payment_intent_succeeded(data: dict[str, Any]) -> None:
    """
    Fires when a payment completes successfully.
    Upgrades the user to PRO if this was a subscription payment.
    """
    payment_intent = data["object"]
    customer_id = payment_intent.get("customer")
    metadata = payment_intent.get("metadata", {})

    if not customer_id:
        return

    tier = metadata.get("subscription_tier", TIER_PRO)
    user_id = metadata.get("user_id")

    if user_id:
        set_user_tier(user_id, tier)
        invalidate_feature_cache(user_id)


def handle_payment_intent_failed(data: dict[str, Any]) -> None:
    """
    Fires when a payment fails.
    Downgrades user to FREE tier after grace period (handled by scheduler).
    Logs the failure for ops review.
    """
    payment_intent = data["object"]
    customer_id = payment_intent.get("customer")
    last_error = payment_intent.get("last_payment_error", {})

    print(
        f"[STRIPE] Payment failed for customer {customer_id}: "
        f"{last_error.get('message', 'unknown error')}"
    )
    # NOTE: actual downgrade is deferred — see scheduler/downgrade_task.py
    # Immediate downgrade here caused too many false positives on card retries


def handle_subscription_deleted(data: dict[str, Any]) -> None:
    """
    Fires when a subscription is cancelled or expires.
    Immediately downgrades user to FREE tier.

    BUG (discovered 2026-04-20): This handler calls set_user_tier() but
    the users.subscription_tier column did not exist until migration 003.
    Sessions before that migration would cause a DB error here.
    Migration 003 (db/migrations/003_subscription_tier.sql) was created
    to fix this — see incident report in docs/incidents/2026-04-20.md
    """
    subscription = data["object"]
    customer_id = subscription.get("customer")
    metadata = subscription.get("metadata", {})
    user_id = metadata.get("user_id")

    if user_id:
        set_user_tier(user_id, TIER_FREE)
        invalidate_feature_cache(user_id)
        print(f"[STRIPE] Subscription cancelled for user {user_id}, downgraded to FREE")


# Event routing table
EVENT_HANDLERS = {
    "payment_intent.succeeded": handle_payment_intent_succeeded,
    "payment_intent.payment_failed": handle_payment_intent_failed,
    "customer.subscription.deleted": handle_subscription_deleted,
}


def handle_webhook(payload: bytes, sig_header: str) -> dict[str, str]:
    """
    Main entry point. Verifies signature, parses event, dispatches to handler.
    Returns {"status": "ok"} or raises on error.
    """
    verify_signature(payload, sig_header, STRIPE_WEBHOOK_SECRET)

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as e:
        raise WebhookHandlerError(f"Invalid JSON payload: {e}")

    event_type = event.get("type")
    handler = EVENT_HANDLERS.get(event_type)

    if handler:
        handler(event.get("data", {}))
    else:
        print(f"[STRIPE] Unhandled event type: {event_type}")

    return {"status": "ok"}
