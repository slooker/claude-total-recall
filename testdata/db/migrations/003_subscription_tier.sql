-- db/migrations/003_subscription_tier.sql
--
-- Adds the subscription_tier column to the users table.
--
-- INCIDENT CONTEXT (2026-04-20):
-- The billing/tiers.py and webhooks/stripe.py code was deployed before
-- this migration was run in production. The stripe webhook handler called
-- set_user_tier() which executed:
--
--   UPDATE users SET subscription_tier = %s WHERE id = %s
--
-- This failed with:
--   psycopg2.errors.UndefinedColumn: column "subscription_tier" of
--   relation "users" does not exist
--
-- The fix: run this migration, then redeploy.
-- Deployed to production: 2026-04-20 23:14 UTC
-- Verified by: checking pg_attribute for the column post-migration
--
-- Depends on: 001_users.sql

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50)
        NOT NULL DEFAULT 'free'
        CHECK (subscription_tier IN ('free', 'pro', 'enterprise'));

CREATE INDEX idx_users_subscription_tier ON users(subscription_tier);

-- Backfill: any existing users without an explicit tier get 'free'
-- (the DEFAULT above handles new rows; this handles the existing ones)
UPDATE users
SET subscription_tier = 'free'
WHERE subscription_tier IS NULL;

COMMENT ON COLUMN users.subscription_tier IS
    'Subscription tier: free | pro | enterprise. '
    'Managed by billing/tiers.py. Updated via Stripe webhook events.';
