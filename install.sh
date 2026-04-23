#!/usr/bin/env bash
# install.sh — install session-recall into the current project
#
# Run from your project root:
#   bash /path/to/session-recall/install.sh
#
# What it does:
#   1. Copies session-recall.py into .claude/
#   2. Copies hook scripts into .claude/hooks/
#   3. Merges hook config into .claude/settings.json
#   4. Adds the /recall slash command
#   5. Appends the CLAUDE.md snippet

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(pwd)"
CLAUDE_DIR="$PROJECT_DIR/.claude"

echo "Installing session-recall into $PROJECT_DIR"
echo ""

# ── 1. Create .claude structure ───────────────────────────────────────────────
mkdir -p "$CLAUDE_DIR/hooks"
mkdir -p "$CLAUDE_DIR/commands"

# ── 2. Copy the recall script ─────────────────────────────────────────────────
cp "$SCRIPT_DIR/session-recall.py" "$CLAUDE_DIR/session-recall.py"
echo "✅ Copied session-recall.py → .claude/session-recall.py"

# ── 3. Copy hook scripts ──────────────────────────────────────────────────────
cp "$SCRIPT_DIR/.claude/hooks/session-start-recall.sh" "$CLAUDE_DIR/hooks/"
cp "$SCRIPT_DIR/.claude/hooks/session-end-recall.sh"   "$CLAUDE_DIR/hooks/"
chmod +x "$CLAUDE_DIR/hooks/session-start-recall.sh"
chmod +x "$CLAUDE_DIR/hooks/session-end-recall.sh"
echo "✅ Copied hook scripts → .claude/hooks/"

# ── 4. Merge settings.json ────────────────────────────────────────────────────
SETTINGS="$CLAUDE_DIR/settings.json"
NEW_HOOKS='{
  "SessionStart": [{"hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/session-start-recall.sh\""}]}],
  "SessionEnd":   [{"hooks": [{"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/session-end-recall.sh\""}]}]
}'

if [ -f "$SETTINGS" ]; then
  # Merge into existing settings using Python
  python3 - <<PYEOF
import json, sys
with open("$SETTINGS", "r") as f:
    existing = json.load(f)

new_hooks = json.loads('''$NEW_HOOKS''')
hooks = existing.setdefault("hooks", {})

for event, cfg in new_hooks.items():
    if event not in hooks:
        hooks[event] = cfg
    else:
        print(f"  ⚠️  hooks.{event} already exists in settings.json — skipping")

with open("$SETTINGS", "w") as f:
    json.dump(existing, f, indent=2)
PYEOF
  echo "✅ Merged hooks into existing .claude/settings.json"
else
  cp "$SCRIPT_DIR/.claude/settings.json" "$SETTINGS"
  echo "✅ Created .claude/settings.json"
fi

# ── 5. Copy /recall slash command ─────────────────────────────────────────────
if [ ! -f "$CLAUDE_DIR/commands/recall.md" ]; then
  cp "$SCRIPT_DIR/.claude/commands/recall.md" "$CLAUDE_DIR/commands/"
  echo "✅ Added /recall slash command"
else
  echo "  ⚠️  .claude/commands/recall.md already exists — skipping"
fi

# ── 6. Append to CLAUDE.md ────────────────────────────────────────────────────
CLAUDEMD="$PROJECT_DIR/CLAUDE.md"
SNIPPET="$SCRIPT_DIR/CLAUDE.md"

if [ -f "$CLAUDEMD" ]; then
  if grep -q "Session Recall" "$CLAUDEMD" 2>/dev/null; then
    echo "  ⚠️  CLAUDE.md already has Session Recall section — skipping"
  else
    echo "" >> "$CLAUDEMD"
    cat "$SNIPPET" >> "$CLAUDEMD"
    echo "✅ Appended Session Recall section to CLAUDE.md"
  fi
else
  cp "$SNIPPET" "$CLAUDEMD"
  echo "✅ Created CLAUDE.md with Session Recall section"
fi

# ── 7. Quick health check ─────────────────────────────────────────────────────
echo ""
echo "── Health check ─────────────────────────────────────────────────────"
python3 "$CLAUDE_DIR/session-recall.py" health || true

echo ""
echo "🎉 session-recall installed! Restart Claude Code (or /clear) to activate."
echo "   The SessionStart hook will automatically inject context on next open."
echo "   Run /recall any time mid-session for a manual summary."
