#!/bin/bash
# Symlink the symphony skill into Claude Code's skills dir.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills/symphony"
DST="$HOME/.claude/skills/symphony"
mkdir -p "$HOME/.claude/skills"
ln -sfn "$SRC" "$DST"
echo "linked $DST -> $SRC"
echo "Optional: add scripts/ to PATH, e.g. ln -sf $(dirname "$SRC")/../scripts/symphony-dispatch.sh ~/.local/bin/"
