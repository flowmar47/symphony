#!/usr/bin/env bash
# Cursor sessionStart adapter: run session-loader + inject-directives, emit
# Cursor additional_context JSON. Fail-open.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
input="$(cat 2>/dev/null || true)"

# Prefer workspace root from Cursor stdin when present.
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

text=""
if [ -x "$ROOT/inject-directives.sh" ]; then
  text+=$("$ROOT/inject-directives.sh" <<<"$input" 2>/dev/null || true)
  text+=$'\n'
fi
if [ -x "$ROOT/session-loader.sh" ]; then
  text+=$("$ROOT/session-loader.sh" <<<"$input" 2>/dev/null || true)
fi

python3 -c '
import json,sys
text=sys.stdin.read().strip()
if not text:
    print("{}")
else:
    # Cap injection size
    if len(text) > 4000:
        text = text[:4000] + "\n…[truncated]"
    print(json.dumps({"additional_context": text}))
' <<<"$text" 2>/dev/null || echo '{}'
exit 0
