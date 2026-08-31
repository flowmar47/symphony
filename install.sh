#!/bin/bash
# Symlink the symphony skill into Claude Code's skills dir.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills/symphony"
DST="$HOME/.claude/skills/symphony"
mkdir -p "$HOME/.claude/skills"
ln -sfn "$SRC" "$DST"
echo "linked $DST -> $SRC"
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo ""
echo "Optional — dispatcher on PATH:"
echo "  ln -sf $ROOT/scripts/symphony-dispatch.sh ~/.local/bin/symphony-dispatch"
echo "  ln -sf $ROOT/scripts/symphony-status.sh   ~/.local/bin/symphony-status"
echo ""
echo "Optional — Score enforcement hooks (Claude Code): score/hooks/hooks.json uses"
echo "  \${CLAUDE_PLUGIN_ROOT}-relative paths; wire them via a plugin, or copy entries"
echo "  into your settings hooks with CLAUDE_PLUGIN_ROOT=$ROOT/score."
echo "  Cursor adapter: score/hooks/adapters/cursor-shell-guard.py"
