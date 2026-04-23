# session-recall

**Zero-dependency context recall for Claude Code.**  
Automatically injects your recent session history at the start of every session — before you type a word.

Inspired by [auto-memory for GitHub Copilot CLI](https://github.com/dezgit2025/auto-memory).  
Same idea, built natively for Claude Code's JSONL session format.

---

## The problem

Every time you open a new Claude Code session, it has no memory of what you were doing. You spend tokens and time re-explaining context that Claude already knew an hour ago.

## The fix

Claude Code writes a complete JSONL transcript of every session to `~/.claude/projects/<your-project>/`. This tool reads those files and injects a compact summary as a `SessionStart` hook — automatically, before your first message.

---

## Install (one command)

```bash
# From your project root:
bash /path/to/session-recall/install.sh
```

Then **restart Claude Code** (close and reopen the panel). The hook activates on the next session open.

### What install does
- Copies `session-recall.py` → `.claude/session-recall.py`
- Copies hook script → `.claude/hooks/session-start-recall.sh`
- Merges `SessionStart` hook into `.claude/settings.json`
- Adds `/recall` slash command to `.claude/commands/`
- Appends a Session Recall section to `CLAUDE.md`

---

## Usage

**Automatic** — just open or resume a session. You'll see something like:

```
=== Session Recall: myapp ===
── Session 1 (1.0h ago) ──
Task: Fix the JWT refresh token flow we left incomplete yesterday
Modified: src/auth/jwt.py, tests/test_auth.py
Read: src/auth/jwt.py, src/auth/middleware.py
── Session 2 (18.0h ago) ──
Task: Implemented JWT auth — middleware and token signing done. Refresh flow TODO.
Modified: src/auth/jwt.py, src/auth/middleware.py
Read: src/auth/jwt.py
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

## `/clear` and `/compact` behavior

These two commands behave differently and it's worth understanding the distinction.

**`/compact`** works seamlessly with session-recall. It writes a summary record to the JSONL file before compressing the context. The next time you open a session, recall will show that summary — often more useful than the raw prompt list.

**`/clear`** does **not** re-trigger the `SessionStart` hook. Claude Code does not fire a new session event on `/clear` — it resets the conversation context but stays in the same session. This means:

- The recall block from session open is gone
- Claude has no memory of the files and context established at the start of the session
- Your next message starts cold

**Fix:** run `/recall` immediately after `/clear`. It reads the JSONL files fresh and re-injects the context summary as a one-shot response. One command, same result.

There is currently no Claude Code hook that fires on `/clear` (and custom commands cannot override built-in commands), so this cannot be made fully automatic. The `/recall` command is the intended recovery path.

---

## File structure after install

```
your-project/
├── CLAUDE.md                          ← Session Recall section appended
└── .claude/
    ├── settings.json                  ← SessionStart hook added
    ├── session-recall.py              ← The recall engine
    ├── hooks/
    │   └── session-start-recall.sh   ← Fires automatically on session open
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

### Token cost

Based on a [controlled benchmark](HOW_I_TESTED.md) against a 4-prompt session on a Python codebase:

| | After P1 | After P2 | After P3 | After P4 |
|---|---|---|---|---|
| Without recall | 1,134 | 3,256 | 5,190 | 8,235 |
| With recall | 959 | 2,224 | 3,773 | 6,175 |
| **Savings** | **175** | **1,032** | **1,417** | **2,060** |

Savings grow with each prompt because without recall, Claude's discovery tool calls accumulate in the context window and inflate the cost of every subsequent message. With recall, Claude navigates directly to the relevant files and that overhead never builds up.

---

## Requirements

- Python 3.8+ (stdlib only — no pip installs)
- Claude Code with hooks support
- macOS, Linux, or Windows (Git Bash)

---

## Global install (optional)

To activate across all projects without copying files into each one:

```bash
bash /path/to/session-recall/install-global.sh
```

This installs the recall script and hook into `~/.claude/` so it fires for every Claude Code project on your machine.

---

## Limitations

- Read-only — never writes to your session database
- Local only — history is per-machine
- No semantic search — matches by recency and file path, not meaning
- `/clear` does not re-trigger the hook — run `/recall` manually to recover (see above)
- Summaries only appear if Claude ran `/compact` before the session ended

---

MIT License. Not affiliated with Anthropic.
