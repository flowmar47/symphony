#!/bin/bash
# Install a complete committed package for Codex and/or Claude, without host config edits.
set -euo pipefail
SYMPHONY_SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -B "$SYMPHONY_SOURCE_ROOT/scripts/install_skill.py" "$@"
