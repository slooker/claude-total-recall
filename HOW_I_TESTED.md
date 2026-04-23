# How to run the benchmark test

This guide walks through a controlled comparison of Claude Code token usage
with and without session-recall enabled. The two test directories are
identical in every way except one line in `.claude/settings.json`.

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

Both directories have identical codebases and identical JSONL session
history. The only difference is whether the `SessionStart` hook fires.

To verify they are identical except for `settings.json`:

```bash
diff -r ../testdata-cold ../testdata-recall
```

---

## Step 2 — Run A (cold start)

1. Open `../testdata-cold` as a folder in VS Code
2. Open the Claude Code panel
3. Send each prompt below, one at a time
4. After **each prompt**, open a Git Bash terminal in that directory and run:
   ```bash
   ./show-tokens.sh
   ```
5. Record the cumulative token totals in the results table below

---

## Step 3 — Run B (with session-recall)

1. Open `../testdata-recall` as a folder in VS Code
2. Open the Claude Code panel
3. You should see a `--- SESSION RECALL ---` block appear automatically
   before you type anything. If you don't see it, see Troubleshooting below.
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

| | After Prompt 1 | After Prompt 2 | After Prompt 3 | After Prompt 4 |
|---|---|---|---|---|
| **Run A input tokens** | | | | |
| **Run A output tokens** | | | | |
| **Run B input tokens** | | | | |
| **Run B output tokens** | | | | |
| **Input difference** | | | | |

---

## What to look for

**Tool calls** — In Run A, prompts 1 and 2 will trigger file discovery:
Claude has to search the codebase to find which migration was created and
which files are related. Each tool call (Read, Grep, Glob) consumes input
tokens. Watch for lines like `Reading src/billing/tiers.py...` in the
response — each one costs tokens.

**Direct answers** — In Run B, the session recall block already names
`db/migrations/003_subscription_tier.sql`, `src/billing/tiers.py`, and
`src/webhooks/stripe.py`. Claude goes straight to those files with no
discovery overhead.

**Cumulative gap** — The token difference typically grows across prompts
because Run A's tool calls add to the context window, making every
subsequent prompt more expensive.

**Quality** — Run B's post-incident report (Prompt 4) should be more
complete and accurate because Claude had correct context from the start
rather than piecing it together through searches.

---

## Troubleshooting

**`--- SESSION RECALL ---` doesn't appear in testdata-recall**

The `SessionStart` hook only fires when a session opens fresh. `/clear`
is not enough. Close the Claude Code panel completely and reopen it.

On Windows, also check that the hook script runs without errors:

```bash
bash .claude/hooks/session-start-recall.sh
```

If it produces no output, run the recall script directly to isolate the issue:

```bash
PYTHONUTF8=1 python3 .claude/session-recall.py --text --limit 3 --days 7
```

**`show-tokens.sh` returns zero**

On Windows with Git Bash, `pwd` returns a Unix-style path (`/c/Users/...`)
but Claude Code encodes using the Windows path (`C:\Users\...`). The script
uses `pwd -W` to handle this, but if it still fails run:

```bash
ls ~/.claude/projects/
```

Find the folder matching your project name and check it contains `.jsonl` files.

**Setup script says "testdata/ source not found"**

Run `setup-benchmark.py` from inside the `claude-total-recall` directory,
not from the parent directory.

---

## Re-running the test

The setup script is safe to run multiple times. It wipes and recreates both
directories and re-seeds the JSONL history from scratch each time:

```bash
python3 setup-benchmark.py
```