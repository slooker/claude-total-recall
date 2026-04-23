"""
src/billing/tiers.py

Defines subscription tiers and the logic for reading/writing a user's
current tier. Tiers are stored in the users.subscription_tier column,
which was added in db/migrations/003_subscription_tier.sql.
"""

from dataclasses import dataclass
from typing import Optional
import db  # thin wrapper around psycopg2

TIER_FREE = "free"
TIER_PRO = "pro"
TIER_ENTERPRISE = "enterprise"

VALID_TIERS = {TIER_FREE, TIER_PRO, TIER_ENTERPRISE}


@dataclass
class TierConfig:
    name: str
    max_projects: Optional[int]   # None = unlimited
    priority_support: bool
    sso_enabled: bool
    audit_logs: bool
    api_rate_limit: int           # requests per minute


TIER_CONFIGS = {
    TIER_FREE: TierConfig(
        name="Free",
        max_projects=3,
        priority_support=False,
        sso_enabled=False,
        audit_logs=False,
        api_rate_limit=60,
    ),
    TIER_PRO: TierConfig(
        name="Pro",
        max_projects=None,
        priority_support=True,
        sso_enabled=False,
        audit_logs=False,
        api_rate_limit=600,
    ),
    TIER_ENTERPRISE: TierConfig(
        name="Enterprise",
        max_projects=None,
        priority_support=True,
        sso_enabled=True,
        audit_logs=True,
        api_rate_limit=6000,
    ),
}


def get_user_tier(user_id: str) -> str:
    """
    Returns the user's current subscription tier.
    Defaults to TIER_FREE if the column is NULL or user not found.

    NOTE: requires migration 003 to have run — the subscription_tier
    column must exist on the users table.
    """
    row = db.fetchone(
        "SELECT subscription_tier FROM users WHERE id = %s",
        (user_id,)
    )
    if row is None or row["subscription_tier"] is None:
        return TIER_FREE
    return row["subscription_tier"]


def set_user_tier(user_id: str, tier: str) -> None:
    """
    Updates the user's subscription tier in the database.

    This was the operation that failed during the 2026-04-20 incident —
    the subscription_tier column didn't exist yet because migration 003
    had not been run in production. The fix was to run the migration and
    redeploy. See db/migrations/003_subscription_tier.sql.
    """
    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier: {tier!r}. Must be one of {VALID_TIERS}")

    db.execute(
        "UPDATE users SET subscription_tier = %s WHERE id = %s",
        (tier, user_id)
    )


def get_tier_config(tier: str) -> TierConfig:
    """Returns the TierConfig for the given tier name."""
    if tier not in TIER_CONFIGS:
        raise ValueError(f"Unknown tier: {tier!r}")
    return TIER_CONFIGS[tier]


def is_feature_allowed(user_id: str, feature: str) -> bool:
    """
    Convenience wrapper — checks if a user's current tier allows a feature.
    See billing/features.py for the full feature flag system.
    """
    from billing.features import FEATURE_REQUIREMENTS
    tier = get_user_tier(user_id)
    required_tier = FEATURE_REQUIREMENTS.get(feature)
    if required_tier is None:
        return True  # unknown features are allowed by default
    tier_order = [TIER_FREE, TIER_PRO, TIER_ENTERPRISE]
    return tier_order.index(tier) >= tier_order.index(required_tier)
