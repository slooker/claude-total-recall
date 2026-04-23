---
description: Show recent session history, or run /recall health for diagnostics
allowed-tools: Bash
---

Arguments: $ARGUMENTS

If the argument is "health", run the following and report the full output as-is:

```bash
PYTHONUTF8=1 python3 .claude/total-recall.py health
```

Otherwise, run this and summarize the output concisely:

```bash
PYTHONUTF8=1 python3 .claude/total-recall.py --text --limit 5 --days 7
```

Focus on:
1. What was I working on most recently?
2. Which files were modified?
3. Were there any unfinished tasks or next steps mentioned?

Keep the summary to 3-5 bullet points. Don't re-read the files unless I ask.
