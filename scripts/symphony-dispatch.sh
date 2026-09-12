#!/bin/bash
# Thin entry point; models and efforts are discovered by the Python adapter.
set -euo pipefail
SYMPHONY_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -B "$SYMPHONY_SCRIPT_DIR/symphony_dispatch.py" "$@"
