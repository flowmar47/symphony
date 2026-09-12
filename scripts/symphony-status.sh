#!/bin/bash
# Show execution metadata without printing private briefs or model answers.
set -euo pipefail
SYMPHONY_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -B "$SYMPHONY_SCRIPT_DIR/symphony_status.py" "$@"
