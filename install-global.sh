#!/usr/bin/env bash
# install-global.sh — install session-recall ONCE for ALL projects
#
# Instead of copying files into each project's .claude/ folder,
# this puts session-recall in ~/.claude/ and wires it globally.
# Every Claude Code project on your machine gets automatic recall.
#
# Run from the session-recall directory:
#   bash install-global.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_CLAUDE="$HOME/.claude"
GLOBAL_HOOKS="$GLOBAL_CLAUDE/hooks"
GLOBAL_COMMANDS="$GLOBAL_CLAUDE/commands"
GLOBAL_SETTINGS="$GLOBAL_CLAUDE/settings.json"

echo "Installing session-recall globally → $GLOBAL_CLAUDE"
echo ""

# ── 1. Create global .claude structure ───────────────────────────────────────
mkdir -p "$GLOBAL_HOOKS"
mkdir -p "$GLOBAL_COMMANDS"

# ── 2. Copy the recall script globally ───────────────────────────────────────
cp "$SCRIPT_DIR/session-recall.py" "$GLOBAL_CLAUDE/session-recall.py"
echo "✅ Copied session-recall.py → ~/.claude/session-recall.py"

# ── 3. Write global hook scripts (use $HOME, not $CLAUDE_PROJECT_DIR) ────────
cat > "$GLOBAL_HOOKS/session-start-recall.sh" << 'HOOKEOF'
#!/usr/bin/env bash
# Global SessionStart hook for session-recall
set -euo pipefail

RECALL_SCRIPT="$HOME/.claude/session-recall.py"

if [ ! -f "$RECALL_SCRIPT" ]; then
  exit 0
fi

OUTPUT=$(python3 "$RECALL_SCRIPT" --limit 3 --days 5 --text 2>/dev/null || true)

if [ -z "$OUTPUT" ]; then
  exit 0
fi

cat <<EOF
--- SESSION RECALL ---
The following is a compact summary of your recent work on this project,
extracted from local session history. Use it to orient immediately without
re-scanning the codebase.

$OUTPUT
--- END SESSION RECALL ---
EOF
HOOKEOF

chmod +x "$GLOBAL_HOOKS/session-start-recall.sh"
echo "✅ Created ~/.claude/hooks/session-start-recall.sh"

# ── 4. Merge into global settings.json ───────────────────────────────────────
NEW_HOOK_START='bash "$HOME/.claude/hooks/session-start-recall.sh"'

if [ -f "$GLOBAL_SETTINGS" ]; then
  python3 - << PYEOF
import json

with open("$GLOBAL_SETTINGS", "r") as f:
    cfg = json.load(f)

hooks = cfg.setdefault("hooks", {})
ss = hooks.setdefault("SessionStart", [])

# Check if already installed
already = any(
    h.get("command", "") == '$NEW_HOOK_START'
    for entry in ss
    for h in entry.get("hooks", [])
)

if already:
    print("  ⚠️  SessionStart hook already present — skipping")
else:
    ss.append({"hooks": [{"type": "command", "command": "$NEW_HOOK_START"}]})
    with open("$GLOBAL_SETTINGS", "w") as f:
        json.dump(cfg, f, indent=2)
    print("✅ Added SessionStart hook to ~/.claude/settings.json")
PYEOF
else
  # Create fresh global settings
  cat > "$GLOBAL_SETTINGS" << SETTINGSEOF
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \\"$HOME/.claude/hooks/session-start-recall.sh\\""
          }
        ]
      }
    ]
  }
}
SETTINGSEOF
  echo "✅ Created ~/.claude/settings.json with SessionStart hook"
fi

# ── 5. Add /recall to global commands ────────────────────────────────────────
GLOBAL_RECALL="$GLOBAL_COMMANDS/recall.md"
if [ ! -f "$GLOBAL_RECALL" ]; then
  cat > "$GLOBAL_RECALL" << 'CMDEOF'
---
description: Show a compact summary of recent session history for this project
allowed-tools: Bash
---

Run this command and summarize the output for me concisely:

```bash
python3 "$HOME/.claude/session-recall.py" --text --limit 5 --days 7
```

Focus on:
1. What was I working on most recently?
2. Which files were modified?
3. Were there any unfinished tasks or next steps mentioned?

Keep the summary to 3-5 bullet points. Don't re-read the files unless I ask.
CMDEOF
  echo "✅ Added /recall to ~/.claude/commands/ (available in all projects)"
else
  echo "  ⚠️  ~/.claude/commands/recall.md already exists — skipping"
fi

# ── 6. Health check ───────────────────────────────────────────────────────────
echo ""
echo "── Health check ─────────────────────────────────────────────────────"
python3 "$GLOBAL_CLAUDE/session-recall.py" health || true

echo ""
echo "🎉 Global install complete!"
echo "   session-recall is now active for ALL your Claude Code projects."
echo "   Restart Claude Code (or /clear) to activate in your current session."
echo ""
echo "   To install per-project instead (for sharing with a team):"
echo "   bash install.sh  (from your project root)"
