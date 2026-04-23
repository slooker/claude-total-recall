# testdata/

Synthetic codebase fixture for benchmarking session-recall token savings.

This is **not real application code**. It exists solely to give Claude
something to search through during the benchmark test, so the cold-start
session has to make actual tool calls (Read, Grep, Glob) while the
recall-primed session can answer from context.

---

## What this simulates

A Python/FastAPI backend that went through 3 development sessions:

**Session 1 (50h ago)** — Set up Stripe webhook handler
- Created `src/webhooks/stripe.py`
- Created `tests/test_stripe_webhook.py`

**Session 2 (20h ago)** — Added subscription tier system
- Created `src/billing/tiers.py`
- Created `src/billing/features.py`
- Updated `src/webhooks/stripe.py` to set user tiers on subscription events
- Note in code: `users.subscription_tier` column migration was pending

**Session 3 (2h ago)** — Fixed production incident
- Migration `003_subscription_tier.sql` was missing from production
- `set_user_tier()` was failing with `UndefinedColumn` error
- Created `db/migrations/003_subscription_tier.sql` to fix it

---

## File structure

```
testdata/
├── src/
│   ├── auth/
│   │   ├── jwt.py              ← JWT token creation & refresh flow
│   │   └── middleware.py       ← FastAPI auth middleware
│   ├── billing/
│   │   ├── tiers.py            ← Subscription tier definitions & DB ops
│   │   └── features.py         ← Feature flag system
│   └── webhooks/
│       └── stripe.py           ← Stripe webhook handler (HMAC verification)
├── db/
│   └── migrations/
│       ├── 001_users.sql       ← Core users table
│       ├── 002_sessions.sql    ← Refresh token session tracking
│       └── 003_subscription_tier.sql  ← THE INCIDENT FIX
└── tests/
    ├── test_stripe_webhook.py
    └── test_auth.py
```

---

## Benchmark test prompts

Run these **identical prompts** in both sessions (cold start vs. recall-primed):

```
Prompt 1:
We had a production incident recently involving a database migration failure.
Find the migration file that was created to fix it, show me its full contents,
and explain what went wrong.

Prompt 2:
Which other source files were involved in that incident? Show me the
relevant code from each one that either caused or was affected by the problem.

Prompt 3:
Looking at the webhook handler and the billing code together, identify
any other potential failure points if a new subscription tier were added.

Prompt 4:
Write a post-incident report covering: what changed, which files were
involved, the root cause, and your recommended safeguards to prevent
recurrence.
```

**What to observe:**
- Cold start: Prompts 1-2 require tool calls to find the files. Each
  tool call (Read, Grep, Glob) consumes tokens. Claude may read the
  wrong files first before finding the right ones.
- Recall-primed: Session recall names `003_subscription_tier.sql`,
  `src/billing/tiers.py`, and `src/webhooks/stripe.py` directly.
  Claude goes straight to those files with no discovery overhead.

**Measure tokens after each prompt with:**
```bash
./show-tokens.sh
```
