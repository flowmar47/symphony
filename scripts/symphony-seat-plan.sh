#!/bin/bash
# Show, check or save the confirmed seat plan; discovery only, no lanes launched.
set -euo pipefail
SYMPHONY_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -B "$SYMPHONY_SCRIPT_DIR/symphony_seatplan.py" "$@"
