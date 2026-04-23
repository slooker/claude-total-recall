#!/usr/bin/env python3
"""
setup-benchmark.py

Creates a fair, reproducible benchmark for total-recall.

Both directories are IDENTICAL in every way:
  - same codebase
  - same seeded JSONL session history in ~/.claude/projects/

The only difference is one line in .claude/settings.json:

  testdata-cold/    — SessionStart hook DISABLED
                      use this for Run A (cold start)

  testdata-recall/  — SessionStart hook ENABLED
                      use this for Run B (with total-recall)

This means anyone can diff the two directories and see exactly one
meaningful difference. The test is fully reproducible and auditable.

Usage:
    python3 setup-benchmark.py

    This script is safe to re-run — it will overwrite existing test dirs.

After running:
    cd ../testdata-cold   → open in Claude Code → Run A (cold)
    cd ../testdata-recall → open in Claude Code → Run B (recall)
"""

import datetime
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent.resolve()
TESTDATA_SRC = SCRIPT_DIR / "testdata"
COLD_DIR = SCRIPT_DIR.parent / "testdata-cold"
RECALL_DIR = SCRIPT_DIR.parent / "testdata-recall"
CLAUDE_DIR = Path.home() / ".claude" / "projects"


# ── Helpers ───────────────────────────────────────────────────────────────────

def encode_path(path: Path) -> str:
    """Mirrors Claude Code's path encoding logic."""
    # On Windows, use the Windows-style path
    try:
        # pwd -W equivalent: get the real Windows path
        p = str(path).replace("/", "\\")
        # Normalise drive letter: C:\... not c:\...
        if len(p) >= 2 and p[1] == ":":
            p = p[0].upper() + p[1:]
    except Exception:
        p = str(path)
    return "".join(c if c.isalnum() else "-" for c in p)


def ts(hours_ago: float) -> str:
    """ISO timestamp N hours in the past."""
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_ago)
    return t.isoformat()


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    # Backdate mtime to match the session age
    first_ts = records[0].get("timestamp", "")
    if first_ts:
        try:
            dt = datetime.datetime.fromisoformat(first_ts)
            mtime = dt.timestamp()
            os.utime(path, (mtime, mtime))
        except Exception:
            pass


# ── Fake JSONL session data ───────────────────────────────────────────────────

def make_session_history(project_path: Path) -> list[tuple[str, list[dict]]]:
    """
    Returns a list of (filename, records) for 3 fake sessions.

    These sessions simulate realistic prior work on the project:
      - Session 1 (50h ago): set up Stripe webhooks
      - Session 2 (20h ago): added subscription tiers
      - Session 3 (2h ago):  fixed the production migration incident

    Crucially, these sessions do NOT contain the answers to the test
    prompts. They establish orientation context only:
      - which files were touched
      - what the overall goal was
      - what the incident was about (but not a full analysis)
    """

    sess1_id = str(uuid.uuid4())
    sess2_id = str(uuid.uuid4())
    sess3_id = str(uuid.uuid4())

    session1 = (
        f"{sess1_id}.jsonl",
        [
            {
                "type": "user",
                "message": {"role": "user", "content": "Set up the Stripe webhook handler for payment events"},
                "timestamp": ts(50),
                "sessionId": sess1_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Write",
                     "input": {"file_path": str(project_path / "src/webhooks/stripe.py")}}
                ]},
                "timestamp": ts(49.9),
                "sessionId": sess1_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Write",
                     "input": {"file_path": str(project_path / "tests/test_stripe_webhook.py")}}
                ]},
                "timestamp": ts(49.8),
                "sessionId": sess1_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "summary",
                "summary": (
                    "Created Stripe webhook handler in src/webhooks/stripe.py. "
                    "Handles payment_intent.succeeded, payment_intent.payment_failed, "
                    "and customer.subscription.deleted events. HMAC signature "
                    "verification implemented using STRIPE_WEBHOOK_SECRET env var. "
                    "Tests written in tests/test_stripe_webhook.py — all passing."
                ),
                "leafUuid": str(uuid.uuid4()),
            },
        ]
    )

    session2 = (
        f"{sess2_id}.jsonl",
        [
            {
                "type": "user",
                "message": {"role": "user", "content": "Add subscription tier logic — free/pro/enterprise with feature flags"},
                "timestamp": ts(20),
                "sessionId": sess2_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Read",
                     "input": {"file_path": str(project_path / "src/webhooks/stripe.py")}}
                ]},
                "timestamp": ts(19.9),
                "sessionId": sess2_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Write",
                     "input": {"file_path": str(project_path / "src/billing/tiers.py")}}
                ]},
                "timestamp": ts(19.8),
                "sessionId": sess2_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Write",
                     "input": {"file_path": str(project_path / "src/billing/features.py")}}
                ]},
                "timestamp": ts(19.7),
                "sessionId": sess2_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Edit",
                     "input": {"file_path": str(project_path / "src/webhooks/stripe.py")}}
                ]},
                "timestamp": ts(19.6),
                "sessionId": sess2_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "summary",
                "summary": (
                    "Added subscription tiers in src/billing/tiers.py "
                    "(FREE: 3 projects, PRO: unlimited + priority support, "
                    "ENTERPRISE: SSO + audit logs). Feature flags in "
                    "src/billing/features.py. Updated src/webhooks/stripe.py "
                    "to call set_user_tier() on subscription events. "
                    "NOTE: users.subscription_tier DB column migration is still pending."
                ),
                "leafUuid": str(uuid.uuid4()),
            },
        ]
    )

    session3 = (
        f"{sess3_id}.jsonl",
        [
            {
                "type": "user",
                "message": {"role": "user", "content": "Production incident — subscription tier migration failed, users.subscription_tier column missing"},
                "timestamp": ts(2),
                "sessionId": sess3_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Read",
                     "input": {"file_path": str(project_path / "src/billing/tiers.py")}}
                ]},
                "timestamp": ts(1.9),
                "sessionId": sess3_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Read",
                     "input": {"file_path": str(project_path / "src/webhooks/stripe.py")}}
                ]},
                "timestamp": ts(1.8),
                "sessionId": sess3_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Write",
                     "input": {"file_path": str(project_path / "db/migrations/003_subscription_tier.sql")}}
                ]},
                "timestamp": ts(1.7),
                "sessionId": sess3_id,
                "uuid": str(uuid.uuid4()),
                "parentUuid": None,
            },
            # Intentionally NO summary — session ended abruptly after the fix
            # This tests that recall still works when there's no compaction summary
        ]
    )

    return [session1, session2, session3]


# ── Main ──────────────────────────────────────────────────────────────────────

SETTINGS_HOOK_ENABLED = {
    "hooks": {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/session-start-total-recall.sh\""
                    }
                ]
            }
        ]
    }
}

SETTINGS_HOOK_DISABLED = {
    "_comment": "total-recall hook is intentionally disabled for cold-start benchmark",
    "hooks": {}
}


def main():
    if not TESTDATA_SRC.exists():
        print(f"ERROR: testdata/ source not found at {TESTDATA_SRC}")
        print("       Run this script from inside the claude-total-recall directory.")
        sys.exit(1)

    print("Setting up benchmark test directories...")
    print()

    # ── 1. Create both directories from the same source ───────────────────────
    for target_dir in [COLD_DIR, RECALL_DIR]:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(TESTDATA_SRC, target_dir)

    print(f"✅ Created {COLD_DIR}")
    print(f"✅ Created {RECALL_DIR}")
    print(f"   Both directories are identical copies of testdata/")

    # ── 2. Seed IDENTICAL JSONL history into BOTH project dirs ───────────────
    # We use the same session UUIDs and timestamps for both so the histories
    # are byte-for-byte identical. Only the encoded path differs.
    print()

    # Generate sessions once, using RECALL_DIR paths in the content
    # (file paths in tool_use records — these are cosmetic, not functional)
    sessions = make_session_history(RECALL_DIR)

    for label, target_dir in [("cold", COLD_DIR), ("recall", RECALL_DIR)]:
        encoded = encode_path(target_dir)
        history_dir = CLAUDE_DIR / encoded
        history_dir.mkdir(parents=True, exist_ok=True)

        # Clear any existing history
        for f in history_dir.glob("*.jsonl"):
            f.unlink()

        # Write identical sessions for each dir
        # Re-generate with this dir's paths so file references are accurate
        dir_sessions = make_session_history(target_dir)
        for filename, records in dir_sessions:
            write_jsonl(history_dir / filename, records)

        print(f"✅ Seeded {len(sessions)} sessions → {history_dir}")

    # ── 3. Copy total-recall tools into both dirs ───────────────────────────
    for target_dir in [COLD_DIR, RECALL_DIR]:
        dot_claude = target_dir / ".claude"
        dot_claude.mkdir(exist_ok=True)
        (dot_claude / "hooks").mkdir(exist_ok=True)
        (dot_claude / "commands").mkdir(exist_ok=True)

        shutil.copy(SCRIPT_DIR / ".claude" / "total-recall.py",
                    dot_claude / "total-recall.py")
        shutil.copy(SCRIPT_DIR / ".claude" / "hooks" / "session-start-total-recall.sh",
                    dot_claude / "hooks" / "session-start-total-recall.sh")
        shutil.copy(SCRIPT_DIR / ".claude" / "commands" / "recall.md",
                    dot_claude / "commands" / "recall.md")
        shutil.copy(SCRIPT_DIR / "show-tokens.sh", target_dir / "show-tokens.sh")

    # ── 4. Write settings.json — THE ONLY DIFFERENCE ─────────────────────────
    cold_settings = COLD_DIR / ".claude" / "settings.json"
    recall_settings = RECALL_DIR / ".claude" / "settings.json"

    with open(cold_settings, "w") as f:
        json.dump(SETTINGS_HOOK_DISABLED, f, indent=2)

    with open(recall_settings, "w") as f:
        json.dump(SETTINGS_HOOK_ENABLED, f, indent=2)

    print()
    print(f"✅ testdata-cold/.claude/settings.json   → hook DISABLED")
    print(f"✅ testdata-recall/.claude/settings.json → hook ENABLED")
    print(f"   This is the only difference between the two directories.")

    # ── 5. Verify recall reads the seeded history correctly ───────────────────
    print()
    print("── Verifying recall output for testdata-recall ──────────────────────")
    import subprocess
    result = subprocess.run(
        ["python3", str(RECALL_DIR / ".claude" / "total-recall.py"),
         "--text", "--limit", "3", "--days", "7"],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONUTF8": "1"}
    )
    if result.stdout.strip():
        print(result.stdout)
    else:
        print("WARNING: recall produced no output — check path encoding")
        if result.stderr:
            print("stderr:", result.stderr)

    # ── 6. Print instructions ─────────────────────────────────────────────────
    print()
    print("═" * 60)
    print("BENCHMARK READY")
    print("═" * 60)
    print()
    print("Run A — cold start (hook disabled, history present but ignored):")
    print(f"  cd {COLD_DIR}")
    print(f"  # Open in VS Code → open Claude Code")
    print(f"  # Run the 4 test prompts")
    print(f"  # Run ./show-tokens.sh after each prompt")
    print()
    print("Run B — with total-recall (hook enabled, history injected):")
    print(f"  cd {RECALL_DIR}")
    print(f"  # Open in VS Code → open Claude Code")
    print(f"  # You should see --- SESSION RECALL --- at the top")
    print(f"  # Run the same 4 test prompts")
    print(f"  # Run ./show-tokens.sh after each prompt")
    print()
    print("To verify the directories are identical except settings.json:")
    print(f"  diff -r {COLD_DIR} {RECALL_DIR}")
    print()
    print("Test prompts (identical for both runs):")
    print("""
  Prompt 1:
  We had a production incident recently involving a database migration
  failure. Find the migration file that was created to fix it, show me
  its full contents, and explain what went wrong.

  Prompt 2:
  Which other source files were involved in that incident? Show me the
  relevant code from each one that either caused or was affected by
  the problem.

  Prompt 3:
  Looking at the webhook handler and the billing code together, identify
  any other potential failure points if a new subscription tier were added.

  Prompt 4:
  Write a post-incident report covering: what changed, which files were
  involved, the root cause, and recommended safeguards to prevent
  recurrence.
""")


if __name__ == "__main__":
    main()
