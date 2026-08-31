#!/usr/bin/env bash
# Cursor stop adapter: run delivery-gate.sh; map block → followup_message.
# Honors loop_count; fail-open.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
input="$(cat 2>/dev/null || true)"

proj="$(printf '%s' "$input" | python3 -c '
import json,sys,os
try:
    d=json.load(sys.stdin)
    roots=d.get("workspace_roots") or []
    print(roots[0] if roots else os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
except Exception:
    print(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
' 2>/dev/null)"
export CLAUDE_PROJECT_DIR="${proj:-$PWD}"

# Skip follow-up if aborted/error or loop exhausted
meta="$(printf '%s' "$input" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    d={}
status=d.get("status","completed")
loop=int(d.get("loop_count") or 0)
active=bool(d.get("stop_hook_active") or False)
print(f"{status}\t{loop}\t{active}")
' 2>/dev/null || echo 'completed	0	False')"

status="$(printf '%s' "$meta" | cut -f1)"
loop="$(printf '%s' "$meta" | cut -f2)"
active="$(printf '%s' "$meta" | cut -f3)"

if [ "$status" != "completed" ] || [ "$active" = "True" ] || [ "${loop:-0}" -ge 5 ]; then
  echo '{}'
  exit 0
fi

# Feed Claude-shaped stop input (include stop_hook_active false)
gate_in="$(printf '%s' "$input" | python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
d["stop_hook_active"]=False
print(json.dumps(d))
' 2>/dev/null || echo '{}')"

out="$(printf '%s' "$gate_in" | bash "$ROOT/delivery-gate.sh" 2>/dev/null || true)"

python3 -c '
import json,sys
raw=sys.stdin.read().strip()
if not raw:
    print("{}"); raise SystemExit
try:
    d=json.loads(raw)
except Exception:
    print("{}"); raise SystemExit
# Claude decision:block → Cursor followup_message (also accepted as-is per Cursor docs)
if d.get("decision")=="block" and d.get("reason"):
    print(json.dumps({"followup_message": d["reason"]}))
elif d.get("followup_message"):
    print(json.dumps({"followup_message": d["followup_message"]}))
else:
    print("{}")
' <<<"$out" 2>/dev/null || echo '{}'
exit 0
