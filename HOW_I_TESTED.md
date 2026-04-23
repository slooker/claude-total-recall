# How to run the benchmark test

This guide walks through a controlled comparison of Claude Code token usage
with and without session-recall enabled.

The two test directories are byte-for-byte identical — same codebase, same
seeded JSONL session history — differing in exactly one thing: whether the
`SessionStart` hook is enabled. You can verify this yourself:

```bash
diff -r ../testdata-cold ../testdata-recall
```

Expected output (the only difference):

```diff
diff -r testdata-cold/.claude/settings.json testdata-recall/.claude/settings.json
2,3c2,13
<   "_comment": "session-recall hook is intentionally disabled for cold-start benchmark",
<   "hooks": {}
---
>   "hooks": {
>     "SessionStart": [
>       {
>         "hooks": [
>           {
>             "type": "command",
>             "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/session-start-recall.sh\""
>           }
>         ]
>       }
>     ]
>   }
```

---

## Prerequisites

- Python 3.8+
- Claude Code installed and authenticated in VS Code
- Git Bash (Windows) or any terminal (macOS/Linux)
- This repo cloned locally

---

## Step 1 — Run the setup script

From inside the `claude-total-recall` directory:

```bash
python3 setup-benchmark.py
```

This creates two sibling directories:

| Directory | Session history | Hook |
|---|---|---|
| `../testdata-cold/` | ✅ seeded | ❌ disabled |
| `../testdata-recall/` | ✅ seeded | ✅ enabled |

The seeded JSONL history simulates three prior working sessions on the
testdata project: the original subscription tier feature, a failed migration
incident, and the fix. This is the history session-recall will summarize.

---

## Step 2 — Run A (cold start, no recall)

1. Open `../testdata-cold` as a folder in VS Code
2. Open the Claude Code panel — you should **not** see a session recall block
3. Send each prompt below, one at a time, word for word
4. After **each prompt**, open a Git Bash terminal in that directory and run:
   ```bash
   ./show-tokens.sh
   ```
5. Record the cumulative totals in the results table below

---

## Step 3 — Run B (with session-recall)

1. Open `../testdata-recall` as a folder in VS Code
2. Open the Claude Code panel
3. Before typing anything, you should see a block like:
   ```
   === Session Recall: testdata-recall ===
   ── Session 1 (Xh ago) ──
   Task: Production incident — subscription tier migration failed,
   Modified: db/migrations/003_subscription_tier.sql
   Read: src/billing/tiers.py, src/webhooks/stripe.py
   ...
   ```
   If you don't see it, see Troubleshooting below.
4. Send the **identical prompts** from Step 2, one at a time
5. After **each prompt**, run `./show-tokens.sh` and record the totals

---

## Test prompts

Send these **word for word** in both runs.

**Prompt 1**
```
We had a production incident recently involving a database migration failure.
Find the migration file that was created to fix it, show me its full contents,
and explain what went wrong.
```

**Prompt 2**
```
Which other source files were involved in that incident? Show me the relevant
code from each one that either caused or was affected by the problem.
```

**Prompt 3**
```
Looking at the webhook handler and the billing code together, identify any
other potential failure points if a new subscription tier were added.
```

**Prompt 4**
```
Write a post-incident report covering: what changed, which files were
involved, the root cause, and recommended safeguards to prevent recurrence.
```

---

## Results table

Fill this in as you go.

| | After P1 | After P2 | After P3 | After P4 |
|---|---|---|---|---|
| **Run A (no recall)** | | | | |
| **Run B (with recall)** | | | | |
| **Savings** | | | | |

### Reference results (April 2026, claude-sonnet-4-6)

| | After P1 | After P2 | After P3 | After P4 |
|---|---|---|---|---|
| **Run A (no recall)** | 1,134 | 3,256 | 5,190 | 8,235 |
| **Run B (with recall)** | 959 | 2,224 | 3,773 | 6,175 |
| **Savings** | 175 | 1,032 | 1,417 | 2,060 |

Token counts are cumulative totals (input + output) from `show-tokens.sh`.
Savings grow with each prompt because Run A's discovery tool calls accumulate
in the context window, making every subsequent message more expensive.

---

## What to look for

**Tool calls in Run A** — Prompts 1 and 2 trigger file discovery. Claude has
to search the codebase to find the migration file and related source files.
Each tool call (Read, Grep, Glob) costs input tokens, and the tool results
stay in the context window, inflating the cost of every later prompt.

**Direct answers in Run B** — The session recall block names
`db/migrations/003_subscription_tier.sql`, `src/billing/tiers.py`, and
`src/webhooks/stripe.py` up front. Claude goes straight to those files with
no discovery pass.

**Compounding savings** — Because Run A's growing context makes each prompt
more expensive, the gap widens across the session rather than staying flat.
By Prompt 4 the savings are 25% of Run A's total token usage.

**Quality** — Run B's post-incident report (Prompt 4) tends to be more
complete because Claude had accurate file context from the start rather than
piecing it together through search.

---

## Troubleshooting

**No session recall block in testdata-recall**

The `SessionStart` hook only fires when a new session opens. `/clear` is not
enough — close the Claude Code panel completely and reopen it (or open the
folder in a fresh VS Code window).

To confirm the hook is wired correctly:
```bash
cat ../testdata-recall/.claude/settings.json
```

To run the hook manually and see its output:
```bash
cd ../testdata-recall
bash .claude/hooks/session-start-recall.sh
```

To run the recall script directly and isolate issues:
```bash
cd ../testdata-recall
PYTHONUTF8=1 python3 .claude/session-recall.py --text --limit 3 --days 7
```

**`show-tokens.sh` returns zero**

On Windows, Git Bash's `pwd` returns a Unix-style path (`/c/Users/...`) but
Claude Code stores session data under the Windows path (`C:\Users\...`). The
script uses `pwd -W` to handle this. If it still fails:

```bash
ls ~/.claude/projects/
```

Find the folder matching your project path and confirm it contains `.jsonl`
files. If it's empty, Claude Code hasn't written any session data yet —
complete at least one prompt exchange first.

**Setup script says "testdata/ source not found"**

Run `setup-benchmark.py` from inside the `claude-total-recall` directory,
not the parent:

```bash
cd claude-total-recall
python3 setup-benchmark.py
```

---

## Re-running the test

The setup script is safe to run multiple times. It wipes and recreates both
directories and re-seeds the JSONL history from scratch each time:

```bash
python3 setup-benchmark.py
```

Re-seeding is important: if you ran the benchmark and the JSONL files now
contain your actual test session, the recall output will include those
sessions and skew the results.
