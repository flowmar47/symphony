#!/usr/bin/env bash
# ENFORCES: Prime Directive 1 + Integrity I-1 (no "done" without a verification run) + notes freshness.
# MAPS TO: AUDIT.md rows Directive-1, I-1, §6 verification, session-state-management. See MEMORY.md 2026-07-06.
# TEST: log an 'edit' of a .py after the last 'verify' → echo '{}' | bash delivery-gate.sh (expect block JSON). A .md/.json-only edit must NOT block.
#
# Stop hook: block finishing when a CODE file was edited this session but no test/build/lint ran
# SINCE that edit (per evidence.log), or WORKING_NOTES.md is missing. Docs/config-only turns
# (.md/.json/.yaml/.toml/.txt/…) are NOT gated — their verification is validity + review, not a
# build. Exit via {"decision":"block"} (verified Stop behavior). Fail-safe: no log / any error →
# allow. Loop guard: honors stop_hook_active so it can never block indefinitely.
set -uo pipefail

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
log="$proj/.claude/logs/evidence.log"
notes="$proj/WORKING_NOTES.md"

input="$(cat 2>/dev/null || true)"

# Loop guard: if we're already inside a stop-hook continuation, don't block again.
active="$(printf '%s' "$input" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("stop_hook_active", False))
except Exception: print(False)' 2>/dev/null)"
[ "$active" = "True" ] && exit 0

# No evidence log → nothing to assert against; allow (fail-safe).
[ -f "$log" ] || exit 0

# Tab-separated log: ts \t kind \t tool \t target \t out.
# Gate only on CODE edits — files with a real build/test story. Docs/config (.md/.json/.yaml/
# .toml/.txt/…) are excluded so documentation- and config-only turns are not forced to run a
# build that does not exist for them; their correct verification is validity + review.
last_verify="$(awk -F'\t' '$2=="verify"{n=NR} END{print n+0}' "$log" 2>/dev/null || echo 0)"
last_code_edit="$(awk -F'\t' '$2=="edit" && tolower($4) ~ /\.(py|pyi|ts|tsx|js|jsx|mjs|cjs|rs|go|java|kt|kts|scala|rb|php|swift|c|cc|cpp|cxx|h|hpp|hh|sh|bash|zsh|sql)([^a-z0-9]|$)/ {n=NR} END{print n+0}' "$log" 2>/dev/null || echo 0)"

# No CODE edits recorded → docs/config-only or read-only turn; nothing to gate. Allow.
[ "$last_code_edit" -eq 0 ] && exit 0

reason=""

# 1. Code edited but no verification ran AFTER the last code edit.
if [ "$last_verify" -lt "$last_code_edit" ]; then
  reason="Source code was edited but no test/build/lint has run since the last edit. "
  reason="${reason}Run the verification (tests + build) and confirm the result before declaring done "
  reason="${reason}(Prime Directive 1 / Integrity I-1). If you truly cannot run it, say so explicitly and hand over the command."
fi

# 2. WORKING_NOTES.md is advisory only (PLAYBOOK §17.3: Trivial/Small skip notes).
# session-loader reminds; do not hard-block delivery on a FLOOR existence check.

if [ -n "$reason" ]; then
  # Block the Stop (verified: decision:block + reason blocks it; loop guard prevents a trap).
  printf '{"decision":"block","reason":%s}\n' \
    "$(printf '%s' "$reason" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '"verification required before stopping"')"
  exit 0
fi

exit 0
