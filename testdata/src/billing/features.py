"""
src/billing/features.py

Feature flag system tied to subscription tiers.
Each feature has a minimum required tier. Users below that tier
are denied access at the API middleware layer.
"""

import functools
from typing import Callable
from billing.tiers import get_user_tier, TIER_FREE, TIER_PRO, TIER_ENTERPRISE

# Maps feature name → minimum tier required to access it
FEATURE_REQUIREMENTS: dict[str, str] = {
    # Free features (everyone gets these)
    "basic_projects": TIER_FREE,
    "api_access": TIER_FREE,
    "community_support": TIER_FREE,

    # Pro features
    "unlimited_projects": TIER_PRO,
    "priority_support": TIER_PRO,
    "advanced_analytics": TIER_PRO,
    "webhooks": TIER_PRO,
    "custom_domains": TIER_PRO,

    # Enterprise features
    "sso": TIER_ENTERPRISE,
    "audit_logs": TIER_ENTERPRISE,
    "saml": TIER_ENTERPRISE,
    "dedicated_support": TIER_ENTERPRISE,
    "custom_contracts": TIER_ENTERPRISE,
    "sla_guarantee": TIER_ENTERPRISE,
}

# Simple in-memory cache for feature checks — invalidated on tier change
_feature_cache: dict[str, dict[str, bool]] = {}


def invalidate_feature_cache(user_id: str) -> None:
    """
    Called by the billing system when a user's tier changes.
    Forces fresh DB reads on next feature check.
    """
    _feature_cache.pop(user_id, None)


def check_feature(user_id: str, feature: str) -> bool:
    """
    Returns True if the user's current tier grants access to the feature.
    Results are cached per user until invalidated.
    """
    if user_id not in _feature_cache:
        _feature_cache[user_id] = {}

    if feature not in _feature_cache[user_id]:
        tier = get_user_tier(user_id)
        required = FEATURE_REQUIREMENTS.get(feature, TIER_FREE)
        tier_order = [TIER_FREE, TIER_PRO, TIER_ENTERPRISE]

        try:
            user_rank = tier_order.index(tier)
            required_rank = tier_order.index(required)
            _feature_cache[user_id][feature] = user_rank >= required_rank
        except ValueError:
            # Unknown tier or feature — default deny
            _feature_cache[user_id][feature] = False

    return _feature_cache[user_id][feature]


def require_feature(feature: str) -> Callable:
    """
    Decorator for FastAPI route handlers. Returns 403 if the
    authenticated user doesn't have the required feature.

    Usage:
        @router.get("/webhooks")
        @require_feature("webhooks")
        async def list_webhooks(user_id: str = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from kwargs (injected by FastAPI dependency)
            user_id = kwargs.get("user_id") or kwargs.get("current_user", {}).get("id")
            if not user_id:
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="Not authenticated")

            if not check_feature(user_id, feature):
                from fastapi import HTTPException
                tier = get_user_tier(user_id)
                raise HTTPException(
                    status_code=403,
                    detail=f"Feature '{feature}' requires a higher subscription tier. "
                           f"Current tier: {tier}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
