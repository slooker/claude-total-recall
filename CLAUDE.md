## Session Recall

This project uses **session-recall** for automatic context recovery.

### How it works
- A `SessionStart` hook runs `session-recall.py` automatically when you open
  or resume a session. You'll see a `--- SESSION RECALL ---` block at the top.
- Use that block to orient immediately. Do NOT re-scan the codebase unless the
  recall summary is empty or stale (> 5 days old).

### Manual recall
Run `/recall` at any time mid-session to get a fresh summary of recent work.

### Health check
```bash
python3 .claude/session-recall.py health
```

### Updating recall data
Session recall reads directly from your local `~/.claude/projects/` JSONL files.
No manual updates needed — it's always current.
