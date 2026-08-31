#!/usr/bin/env bash
# Cursor afterFileEdit adapter: map file path into Claude Edit shape for post-edit-verify.
# Emits additional_context on findings; never blocks the edit. Fail-open.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
input="$(cat 2>/dev/null || true)"

mapped="$(printf '%s' "$input" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print("{}"); raise SystemExit
# Cursor afterFileEdit often has file_path / path / edits
path = d.get("file_path") or d.get("path") or ""
if not path and isinstance(d.get("edits"), list) and d["edits"]:
    path = d["edits"][0].get("path") or d["edits"][0].get("file_path") or ""
roots = d.get("workspace_roots") or []
print(json.dumps({
    "tool_name":"Edit",
    "tool_input":{"file_path": path},
    "workspace_roots": roots,
    "_cursor_raw_keys": sorted(d.keys())[:20],
}))
' 2>/dev/null || echo '{}')"

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

# Capture stderr from post-edit-verify (exit 2 = findings)
err="$(printf '%s' "$mapped" | bash "$ROOT/post-edit-verify.sh" 2>&1 >/dev/null)"
ec=$?
if [ "$ec" -eq 2 ] && [ -n "$err" ]; then
  python3 -c 'import json,sys; print(json.dumps({"additional_context": sys.stdin.read()[:3000]}))' <<<"$err" 2>/dev/null || echo '{}'
else
  echo '{}'
fi
exit 0
