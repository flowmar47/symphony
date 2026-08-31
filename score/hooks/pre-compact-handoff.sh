#!/usr/bin/env bash
# ENFORCES: session-state-management skill — survive compaction with a written handoff.
# MAPS TO: AUDIT.md rows session-state-management, §9 large deliverables.
# TEST: echo '{"hook_event_name":"PreCompact","trigger":"auto"}' | bash pre-compact-handoff.sh; tail -n 20 "$CLAUDE_PROJECT_DIR/WORKING_NOTES.md"
#
# PreCompact hook: before context is compacted, stamp a handoff block into WORKING_NOTES.md so
# the post-compaction session can resume cold. Captures git status + recent evidence so the
# next context knows what changed and what ran. Does NOT block compaction (always exits 0);
# purely additive. Fail-safe: any error exits 0.
set -uo pipefail

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
notes="$proj/WORKING_NOTES.md"
log="$proj/.claude/logs/evidence.log"

input="$(cat 2>/dev/null || true)"
trigger="$(printf '%s' "$input" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("trigger","?"))
except Exception: print("?")' 2>/dev/null)"
ts="$(date -u +%FT%TZ 2>/dev/null || echo unknown)"

# Create the notes file with the standard skeleton if absent.
if [ ! -f "$notes" ]; then
  {
    echo "# WORKING NOTES"
    echo
    echo "## Task"
    echo "## Plan"
    echo "## Decisions"
    echo "## Status"
    echo "## Next action"
    echo "## Assumptions & open questions"
  } >"$notes" 2>/dev/null || exit 0
fi

# Gather cheap, objective state.
git_branch="$(git -C "$proj" branch --show-current 2>/dev/null || echo '?')"
git_dirty="$(git -C "$proj" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
git_files="$(git -C "$proj" status --porcelain 2>/dev/null | awk '{print $2}' | head -12 | tr '\n' ' ')"
last_verify="$( [ -f "$log" ] && awk -F'\t' '$2=="verify"{l=$0} END{print l}' "$log" 2>/dev/null | cut -f1,4 || true )"

{
  echo
  echo "<!-- AUTO-HANDOFF (PreCompact/$trigger) $ts -->"
  echo "### Compaction handoff — $ts"
  echo "- Git: branch \`$git_branch\`, $git_dirty uncommitted file(s): $git_files"
  echo "- Last verification run recorded: ${last_verify:-none}"
  echo "- RESUME: re-read the Task/Status/Next-action sections above; trust this file over recollection."
} >>"$notes" 2>/dev/null || exit 0

exit 0
