# session-recall

**Zero-dependency context recall for Claude Code.**  
Automatically injects your recent session history at the start of every session — before you type a word.

Inspired by [auto-memory for GitHub Copilot CLI](https://github.com/dezgit2025/auto-memory).  
Same idea, built natively for Claude Code's JSONL session format.

---

## The problem

Every time you `/clear` or open a new Claude Code session, it has no memory of what you were doing. You spend 5–10 minutes and thousands of tokens re-explaining context that Claude already knew an hour ago.

## The fix

Claude Code writes a complete JSONL transcript of every session to `~/.claude/projects/<your-project>/`. This tool reads those files and injects a compact summary as a `SessionStart` hook — automatically, before your first message, costing ~50 tokens instead of ~10,000.

---

## Install (one command)

```bash
# From your project root:
bash /path/to/session-recall/install.sh
```

Then restart Claude Code or run `/clear`. The hook activates immediately.

### What install does
- Copies `session-recall.py` → `.claude/session-recall.py`
- Copies hook scripts → `.claude/hooks/`
- Merges `SessionStart`/`SessionEnd` hooks into `.claude/settings.json`
- Adds `/recall` slash command to `.claude/commands/`
- Appends a Session Recall section to `CLAUDE.md`

---

## Usage

**Automatic** — just open or resume a session. You'll see:

```
--- SESSION RECALL ---
=== Session Recall: myapp ===

── Session 1 (1.0h ago) ──────────────────
First prompt: Fix the JWT refresh token flow we left incomplete yesterday
Modified: src/auth/jwt.py, tests/test_auth.py
Read: src/auth/jwt.py

── Session 2 (18.0h ago) ──────────────────
Summary: Implemented JWT auth. src/auth/jwt.py and src/auth/middleware.py.
Tests passing. TODO: refresh token flow not yet implemented.
...
--- END SESSION RECALL ---
```

**Manual mid-session** — type `/recall` to get a fresh summary at any point.

**Health check** — verify the tool is set up correctly:
```bash
python3 .claude/session-recall.py health
```

**CLI options:**
```bash
python3 .claude/session-recall.py                  # JSON output, last 3 sessions, 3 days
python3 .claude/session-recall.py --text           # human-readable
python3 .claude/session-recall.py --days 7         # look back 7 days
python3 .claude/session-recall.py --limit 5        # show up to 5 sessions
python3 .claude/session-recall.py health           # diagnostics
```

---

## File structure after install

```
your-project/
├── CLAUDE.md                          ← Session Recall section appended
└── .claude/
    ├── settings.json                  ← SessionStart + SessionEnd hooks
    ├── session-recall.py              ← The recall engine
    ├── hooks/
    │   ├── session-start-recall.sh   ← Fires automatically on session open
    │   └── session-end-recall.sh     ← Logs session end (optional)
    └── commands/
        └── recall.md                 ← /recall slash command
```

---

## How it works

### Session data location

Claude Code stores session transcripts at:
```
~/.claude/projects/<encoded-path>/<session-uuid>.jsonl
```

Where `<encoded-path>` is your project's absolute path with non-alphanumeric characters replaced by `-`.

### What gets extracted (per session)
- **Summary** — Claude's auto-generated compaction summary (if present)
- **First user prompt** — what you asked at the start
- **Modified files** — anything touched by Write/Edit tools
- **Read files** — anything inspected by Read/Grep/Glob tools
- **Timestamps** — how long ago the session was

### Sessions without summaries
If you hit `/clear` abruptly (no compaction), the tool still recovers the prompt and file list from raw tool calls. Nothing is lost.

### Token cost
- Typical recall output: **~80–150 tokens**
- vs. blind codebase re-scan: **~10,000–16,000 tokens**

---

## Requirements

- Python 3.8+ (stdlib only — no pip installs)
- Claude Code with hooks support (v2.0+)
- macOS or Linux

---

## Global install (optional)

To use across all projects without copying files each time:

```bash
# Copy the recall script globally
cp session-recall.py ~/.claude/session-recall.py

# Add to ~/.claude/settings.json (global hooks apply to all projects)
# Edit ~/.claude/settings.json and add the SessionStart hook pointing to:
# bash "$HOME/.claude/hooks/session-start-recall.sh"
```

---

## Limitations

- Read-only — never writes to your session database
- Local only — history is per-machine
- No semantic search — matches by recency and file path, not meaning
- Summaries only exist if Claude ran compaction before `/clear`

---

MIT License. Not affiliated with Anthropic.
