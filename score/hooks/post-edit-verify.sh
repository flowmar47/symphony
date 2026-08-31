#!/usr/bin/env bash
# ENFORCES: Prime Directive 14 + verification-loop skill (verify each unit before the next).
# MAPS TO: AUDIT.md rows Directive-14, verification-loop, I-3 (flags test weakening).
# TEST: echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/x.py"}}' | bash post-edit-verify.sh; echo "exit=$?"  (edit a .py with a syntax error → expect exit 2 + errors)
#
# PostToolUse(Edit|Write|MultiEdit): fast per-file check on the edited source so failures are
# caught at the edit, not discovered at delivery. Runs ONLY a fast typecheck/lint on the single
# touched file (never the full suite — that belongs to the delivery gate / qa-verifier). Exit 2
# feeds errors back to Claude to fix now; any other path exits 0. Fail-safe: never blocks on a
# missing tool or its own error.
set -uo pipefail

input="$(cat 2>/dev/null || true)"
file="$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin); ti=d.get("tool_input",{})
    print(ti.get("file_path") or ti.get("path") or "")
except Exception:
    print("")' 2>/dev/null)"

# Nothing to check.
[ -z "$file" ] || [ ! -f "$file" ] && exit 0

ext="${file##*.}"
out=""      # captured tool output on failure
failed=0

run() { # run <cmd...>; capture combined output, set failed on non-zero
  local o
  if ! o="$("$@" 2>&1)"; then
    failed=1
    out="$out$o"$'\n'
  fi
}

case "$ext" in
  py)
    command -v ruff >/dev/null 2>&1 && run timeout 20 ruff check --quiet -- "$file"
    # pyright is per-project + slow; skip here (delivery gate / qa-verifier covers types).
    ;;
  rs)
    # rustc single-file check is unreliable in a workspace; a syntax-only parse is the safe fast check.
    command -v rustfmt >/dev/null 2>&1 && run timeout 20 rustfmt --check --edition 2021 "$file"
    ;;
  ts | tsx | js | jsx | mjs | cjs)
    command -v eslint >/dev/null 2>&1 && run timeout 25 eslint --no-error-on-unmatched-pattern "$file"
    ;;
  json)
    run python3 -c "import json,sys
try:
    json.load(open(sys.argv[1]))
except Exception as e:
    sys.stderr.write(f'invalid JSON: {e}\n'); sys.exit(1)" "$file"
    ;;
esac

# Extra guard for I-3: only flag NEW skip/ignore markers introduced in the current diff.
case "$file" in
  *test*|*spec*|*_test.*|*.test.*)
    skip_re='(\.skip\b|xit\(|xdescribe\(|@pytest\.mark\.skip|#\[ignore\]|t\.Skip\()'
    # Prefer git diff (staged+unstaged) so pre-existing skips do not trip the gate.
    if command -v git >/dev/null 2>&1 && git -C "$(dirname "$file")" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      if git -C "$(dirname "$file")" diff HEAD -- "$file" 2>/dev/null | grep -E "^\+" | grep -Eiv "^\+\+\+" | grep -Ei "$skip_re" >/dev/null 2>&1; then
        failed=1
        out="$out""NOTE: this edit ADDS a skip/ignore marker — confirm it is not bypassing a failing test (Integrity I-3)."$'\n'
      fi
    fi
    ;;
esac

if [ "$failed" -eq 1 ] && [ -n "$out" ]; then
  # Exit 2 → stderr is fed back to Claude to fix immediately.
  printf 'post-edit check found issues in %s:\n%s\n' "$file" "$out" >&2
  exit 2
fi
exit 0
