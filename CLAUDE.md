## Total Recall

This project uses **total-recall** for automatic context recovery.

### How it works
- A `SessionStart` hook runs `total-recall.py` automatically when you open
  or resume a session. You'll see a `--- SESSION RECALL ---` block at the top.
- Use that block to orient immediately. Do NOT re-scan the codebase unless the
  recall summary is empty or stale (> 5 days old).
- **At the start of every session**, after reading the recall block, output this
  warning visibly to the user as your very first line:
  `⚠️ If you run /clear, Total Recall goes dark. Run /recall immediately after to restore context.`

### Manual recall
Run `/recall` at any time mid-session to get a fresh summary of recent work.

### Health check
```bash
python3 .claude/total-recall.py health
```

### Updating recall data
Session recall reads directly from your local `~/.claude/projects/` JSONL files.
No manual updates needed — it's always current.
