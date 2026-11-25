#!/bin/bash
# Record conductor acceptance/frontier-review status for a completed lane attempt.
set -euo pipefail
SYMPHONY_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -B "$SYMPHONY_SCRIPT_DIR/symphony_status.py" mark "$@"
