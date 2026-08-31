#!/usr/bin/env bash
# ENFORCES: gives the delivery gate + MEMORY.md an objective record (Prime Directive 1, I-1, I-7).
# MAPS TO: AUDIT.md rows Directive-1, I-1, I-7, and the delivery-gate dependency.
# TEST: echo '{"tool_name":"Bash","tool_input":{"command":"pytest -q"},"tool_response":{"text":"3 passed"}}' | bash evidence-log.sh; tail -1 "$CLAUDE_PROJECT_DIR/.claude/logs/evidence.log"
#
# PostToolUse(*): append one objective line per tool call to .claude/logs/evidence.log so
# delivery can check "did a test/build actually run since the last edit?" — not the model's
# word. Always exits 0; logging must never block or fail a tool. No model calls.
set -uo pipefail

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
logdir="$proj/.claude/logs"
log="$logdir/evidence.log"
mkdir -p "$logdir" 2>/dev/null || exit 0

input="$(cat 2>/dev/null || true)"

# Extract tool name, a short target, and a short outcome — classify edit vs verify vs other.
line="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
tool = d.get("tool_name", "?")
ti = d.get("tool_input", {}) or {}
tr = d.get("tool_response", {}) or {}
target = ti.get("file_path") or ti.get("path") or ti.get("command") or ""
target = " ".join(str(target).split())[:120]

# Classify: is this an edit, a verification run, or other?
kind = "other"
if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
    kind = "edit"
elif tool in ("Bash", "Shell", "shell"):
    # Cursor posts Shell; Claude Code posts Bash. Same verification classifier.
    c = str(ti.get("command", "") or ti.get("cmd", "") or "")
    if any(k in c for k in ("test", "pytest", "cargo test", "cargo check", "jest", "vitest",
                            "go test", "go vet", "build", "cargo build", "tsc", "npm run",
                            "pnpm", "make", "lint", "ruff", "clippy", "eslint", "mypy",
                            "pyright", "shellcheck", "bash -n", "sh -n", "json.tool",
                            "py_compile", "node --check", "--check", "--dry-run",
                            "verify", "validate", "deno check", "deno test", "deno lint")):
        kind = "verify"

# Short outcome from the response text if present.
txt = ""
if isinstance(tr, dict):
    txt = str(tr.get("text") or tr.get("stdout") or "")
elif isinstance(tr, str):
    txt = tr
txt = " ".join(txt.split())[:80]
print(f"{kind}\t{tool}\t{target}\t{txt}")
' 2>/dev/null)"

[ -z "$line" ] && exit 0
ts="$(date -u +%FT%TZ 2>/dev/null || echo unknown)"
printf '%s\t%s\n' "$ts" "$line" >>"$log" 2>/dev/null || true
exit 0
