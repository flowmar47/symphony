#!/usr/bin/env bash
# Cursor postToolUse adapter: normalize tool payload into Claude evidence-log shape.
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

mapped="$(printf '%s' "$input" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print("{}"); raise SystemExit
# Cursor may use tool_name, toolName, or name
tool = d.get("tool_name") or d.get("toolName") or d.get("name") or d.get("tool") or "?"
# Map Cursor Shell → Bash for classifier
if tool in ("Shell", "shell", "Bash"):
    tool = "Bash"
ti = d.get("tool_input") or d.get("input") or d.get("args") or {}
if not isinstance(ti, dict):
    ti = {}
# Promote top-level command/path if needed
if "command" in d and "command" not in ti:
    ti = {**ti, "command": d.get("command")}
if ("file_path" in d or "path" in d) and "file_path" not in ti:
    ti = {**ti, "file_path": d.get("file_path") or d.get("path")}
# Write/StrReplace/Edit mapping
if tool in ("Write", "StrReplace", "Edit", "edit", "write"):
    tool = "Edit" if tool != "Write" else "Write"
tr = d.get("tool_response") or d.get("result") or d.get("output") or {}
print(json.dumps({"tool_name": tool, "tool_input": ti, "tool_response": tr}))
' 2>/dev/null || echo '{}')"

printf '%s' "$mapped" | bash "$ROOT/evidence-log.sh" >/dev/null 2>&1 || true
echo '{}'
exit 0
