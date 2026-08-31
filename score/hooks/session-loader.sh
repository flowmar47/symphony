#!/usr/bin/env bash
# ENFORCES: session-state-management + operational memory — every session starts oriented.
# MAPS TO: AUDIT.md rows session-state-management, operational memory (MEMORY.md).
# TEST: echo '{"hook_event_name":"SessionStart","source":"startup"}' | bash session-loader.sh  (expect git status + CURRENT-STATUS block + last 3 MEMORY entries on stdout)
#
# SessionStart hook: print git status, the WORKING_NOTES.md CURRENT-STATUS block, and the
# last 3 MEMORY.md entries to stdout. Verified behavior: SessionStart stdout is injected as
# session context. Reads ONLY the marked CURRENT-STATUS record — never a historical Status
# section (the pre-2026-08-24 version printed the FIRST '## Status' match, which surfaced
# months-old state). Also warns (never mutates) on OHMS-GLOBAL drift for the current repo
# and on WORKING_NOTES retention overrun. Read-only; always exits 0; fail-safe on any
# missing file or error. Budget: median ≤ 500 ms over 5 runs.
set -uo pipefail

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
notes="$proj/WORKING_NOTES.md"
memory="$proj/MEMORY.md"
template="$HOME/.claude/ohms-global/template.md"

echo "=== Symphony Score session orientation ==="

# Git state (skip cleanly if not a repo).
if git -C "$proj" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch="$(git -C "$proj" branch --show-current 2>/dev/null || echo '?')"
  # -uno + ignore-submodules keeps this O(index) — full status on the 40-repo workspace
  # costs ~2 s and blew the 500 ms loader budget.
  status="$(git -C "$proj" --no-optional-locks status --porcelain -uno --ignore-submodules=dirty 2>/dev/null)"
  dirty="$(printf '%s' "$status" | grep -c . || true)"
  echo "[git] branch: $branch | modified tracked files: $dirty (untracked/submodule-content not counted)"
  printf '%s\n' "$status" | grep . | head -8 | sed 's/^/       /'
else
  echo "[git] not a git repository"
fi

# Working notes — resume point: the uniquely marked CURRENT-STATUS record only.
if [ -f "$notes" ]; then
  begins="$(grep -c 'CURRENT-STATUS BEGIN' "$notes" 2>/dev/null)"; begins="${begins:-0}"
  ends="$(grep -c 'CURRENT-STATUS END' "$notes" 2>/dev/null)"; ends="${ends:-0}"
  first_begin="$(grep -n 'CURRENT-STATUS BEGIN' "$notes" 2>/dev/null | head -1 | cut -d: -f1)"
  first_end="$(grep -n 'CURRENT-STATUS END' "$notes" 2>/dev/null | head -1 | cut -d: -f1)"
  if [ "$begins" -eq 0 ] && [ "$ends" -eq 0 ]; then
    echo "[working-notes] WORKING_NOTES.md present but has no CURRENT-STATUS block — add one:"
    echo "       <!-- CURRENT-STATUS BEGIN --> ... <!-- CURRENT-STATUS END --> (replace in place each update)"
  elif [ "$begins" -ne 1 ] || [ "$ends" -ne 1 ] || [ "${first_begin:-0}" -ge "${first_end:-0}" ]; then
    echo "[working-notes] malformed CURRENT-STATUS markers (begins=$begins ends=$ends order=${first_begin:-?}/${first_end:-?}) — need exactly one ordered pair; skipping."
  else
    echo "[working-notes] CURRENT-STATUS:"
    awk '/CURRENT-STATUS BEGIN/{f=1; next} /CURRENT-STATUS END/{exit} f' "$notes" 2>/dev/null | head -30 | sed 's/^/       /'
  fi
  lines="$(wc -l < "$notes" | tr -d ' ')"
  [ "$lines" -gt 1500 ] && echo "[working-notes] retention: $lines lines — roll terminal records >2 weeks old to _archive/working-notes/ (owner-approved manifest)."
else
  echo "[working-notes] none yet — create WORKING_NOTES.md when a task exceeds ~30 min or ~10 steps."
fi

# OHMS-GLOBAL drift — current repo only, extracted block digest vs the stored template hash.
tmpl_hash="$HOME/.claude/ohms-global/template.sha256"
if [ -f "$tmpl_hash" ] && [ -f "$proj/AGENTS.md" ] && grep -q 'BEGIN OHMS-GLOBAL' "$proj/AGENTS.md" 2>/dev/null; then
  want="$(tr -d ' \n' < "$tmpl_hash" 2>/dev/null)"
  blk="$(awk '/<!-- BEGIN OHMS-GLOBAL/{f=1} f{print} /<!-- END OHMS-GLOBAL -->/{exit}' "$proj/AGENTS.md" 2>/dev/null)"
  have="$(printf '%s' "$blk" | shasum -a 256 | cut -d' ' -f1)"
  if [ -n "$want" ] && [ "$want" != "$have" ]; then
    echo "[ohms-global] AGENTS.md block differs from ~/.claude/ohms-global/template.md — re-sync: python3 ~/.claude/ohms-global/sync-repo-agents.py --check --repo $proj"
  fi
fi

# Last 3 operational-memory entries (lines beginning with a date, table rows).
if [ -f "$memory" ]; then
  echo "[memory] last 3 MEMORY.md entries:"
  grep -E '^\s*(20[0-9]{2}-[0-9]{2}-[0-9]{2}|\| *20[0-9]{2}-)' "$memory" 2>/dev/null | tail -3 | sed 's/^/       /'
else
  echo "[memory] no MEMORY.md yet."
fi

echo "=== reminder: verify before claiming done; keep the CURRENT-STATUS block current ==="
exit 0
