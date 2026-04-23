#!/usr/bin/env bash
LOG="$CLAUDE_PROJECT_DIR/.claude/hook-test.log"
echo "HOOK FIRED at $(date)" >> "$LOG"
echo "  CLAUDE_PROJECT_DIR=$CLAUDE_PROJECT_DIR" >> "$LOG"
echo "  python3=$(which python3 2>&1)" >> "$LOG"
OUTPUT=$(PYTHONUTF8=1 python3 "$CLAUDE_PROJECT_DIR/.claude/total-recall.py" --text --limit 3 --days 5 2>&1)
echo "  exit_code=$?" >> "$LOG"
echo "  output_len=${#OUTPUT}" >> "$LOG"
echo "$OUTPUT"
echo ""
echo "⚠️  If you run /clear, Total Recall goes dark. Run /recall immediately after to restore context."
