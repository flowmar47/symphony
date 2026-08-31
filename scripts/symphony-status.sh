#!/bin/bash
# symphony-status.sh — show the last N ledger rows (default 12).
set -euo pipefail
LEDGER="${SYMPHONY_LEDGER:-$HOME/.symphony/ledger.jsonl}"
[ -f "$LEDGER" ] || { echo "no ledger at $LEDGER"; exit 0; }
tail -n "${1:-12}" "$LEDGER" | python3 -c '
import json,sys
for line in sys.stdin:
    r=json.loads(line)
    tier=r.get("tier") or r.get("mode") or ""
    print("%s  %-7s %-24s %-5s %-6s %s" % (r.get("at",""),r.get("seat",""),r.get("lane",""),r.get("state",""),tier,r.get("out","")))'
