---
description: Show a compact summary of recent session history for this project
allowed-tools: Bash
---

Run this command and summarize the output for me concisely:

```bash
python3 .claude/session-recall.py --text --limit 5 --days 7
```

Focus on:
1. What was I working on most recently?
2. Which files were modified?
3. Were there any unfinished tasks or next steps mentioned?

Keep the summary to 3-5 bullet points. Don't re-read the files unless I ask.
