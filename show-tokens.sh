#!/usr/bin/env bash

# Convert Git Bash path to Windows-style encoded path that Claude Code uses
WIN_PATH=$(pwd -W 2>/dev/null || pwd)
ENCODED=$(echo "$WIN_PATH" | sed 's/[^a-zA-Z0-9]/-/g')
PROJECT_DIR="$HOME/.claude/projects/$ENCODED"

echo "Looking in: $PROJECT_DIR"

LATEST=$(ls -t "$PROJECT_DIR"/*.jsonl 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
  echo "No session files found."
  echo "Contents of ~/.claude/projects/:"
  ls "$HOME/.claude/projects/" 2>/dev/null
  exit 1
fi

echo "Reading: $(basename $LATEST)"
echo ""

cat "$LATEST" | python -c "
import sys, json
inp, out = 0, 0
for line in sys.stdin:
    try:
        r = json.loads(line)
        u = r.get('message', {}).get('usage', {})
        inp += u.get('input_tokens', 0)
        out += u.get('output_tokens', 0)
    except: pass
print(f'Input tokens:  {inp:,}')
print(f'Output tokens: {out:,}')
print(f'Total:         {inp+out:,}')
"
