#!/bin/bash
# symphony-dispatch.sh — one entry point for delegating a lane to a seat.
#
#   symphony-dispatch.sh builder <medium|high|max> <spec.md> <repo-dir> <lane-name>
#   symphony-dispatch.sh scout   <ask|plan>        <prompt|@file> <dir> <lane-name>
#
# builder: runs Codex CLI headless (workspace-write, approvals off) against a frozen
#          spec; report lands in $SYMPHONY_OUT/<lane>.txt, thread id in the ledger.
# scout:   runs Codex CLI read-only (ask = repo Q&A, plan = +web research via the account's
#          search MCP); answer lands in $SYMPHONY_OUT/<lane>.txt. Empty output fails the lane.
#
# Every run appends one JSON line to $SYMPHONY_LEDGER (default ~/.symphony/ledger.jsonl):
# start/end time, seat, tier/mode, dir, spec/prompt ref, exit code, output path, thread id.
#
# The dispatcher never commits, pushes, or mutates anything outside the lane's own
# working dir — landing is the conductor's job, after host verification.
set -euo pipefail

SEAT="${1:?seat: builder|scout}"; shift
SYMPHONY_OUT="${SYMPHONY_OUT:-${TMPDIR:-/tmp}/symphony}"
SYMPHONY_LEDGER="${SYMPHONY_LEDGER:-$HOME/.symphony/ledger.jsonl}"
mkdir -p "$SYMPHONY_OUT" "$(dirname "$SYMPHONY_LEDGER")"

ledger() { # ledger <json-fields...>
  python3 - "$@" <<'PY' >> "$SYMPHONY_LEDGER"
import json,sys,datetime
row={"at":datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
for kv in sys.argv[1:]:
    k,v=kv.split("=",1); row[k]=v
print(json.dumps(row))
PY
}

case "$SEAT" in
  builder)
    TIER="${1:?tier: medium|high|max}"; SPEC="${2:?spec file}"; DIR="${3:?repo dir}"; LANE="${4:?lane name}"
    case "$TIER" in medium|high|max) ;; *) echo "bad tier: $TIER" >&2; exit 2;; esac
    SPEC="$(cd "$(dirname "$SPEC")" && pwd)/$(basename "$SPEC")"
    [ -f "$SPEC" ] || { echo "spec not found: $SPEC" >&2; exit 2; }
    OUT="$SYMPHONY_OUT/$LANE.txt"
    ledger seat=builder lane="$LANE" tier="$TIER" dir="$DIR" spec="$SPEC" state=start
    # Stream the event log to a file — piping codex through grep -m1 SIGPIPEs it mid-run.
    ( cd "$DIR" && codex exec \
        -c sandbox_mode="workspace-write" -c approval_policy="never" \
        -c model_reasoning_effort="$TIER" \
        --json -o "$OUT" - <<EOF > "$OUT.jsonl" 2>/dev/null
GOAL: Implement the frozen, already-reviewed spec exactly. If a step is impossible as
written, implement the closest faithful version and report the deviation — never redesign.
SPEC: Read $SPEC and follow it. End with a report: files changed, verbatim proof output,
deviations.
EOF
    ) || { ledger seat=builder lane="$LANE" state=fail exit=$?; exit 1; }
    THREAD=$(grep -m1 '"type":"thread.started"' "$OUT.jsonl" | sed -E 's/.*"thread_id":"([^"]+)".*/\1/')
    ledger seat=builder lane="$LANE" state=done tier="$TIER" thread="$THREAD" out="$OUT"
    echo "builder lane '$LANE' done — report: $OUT  thread: $THREAD"
    echo "CONDUCTOR: verify on host before landing (diff, proof commands, scope)."
    ;;
  scout)
    MODE="${1:?mode: ask|plan}"; PROMPT="${2:?prompt or @file}"; DIR="${3:?dir}"; LANE="${4:?lane name}"
    case "$MODE" in ask|plan) ;; *) echo "bad mode: $MODE" >&2; exit 2 ;; esac
    [ "${PROMPT#@}" != "$PROMPT" ] && PROMPT="$(cat "${PROMPT#@}")"
    OUT="$SYMPHONY_OUT/$LANE.txt"
    # Scout engine: read-only Codex (default). ask = repo/knowledge only; plan = web search
    # allowed with citations. Never edits. The brief goes in on stdin, never as a bare argument.
    ENGINE="${SYMPHONY_SCOUT_ENGINE:-codex}"
    WEB_RULE="Do not use web search or fetch; answer from the repository and your own knowledge only."
    [ "$MODE" = plan ] && WEB_RULE="Use web search and fetch freely; cite the URL for every load-bearing claim."
    BRIEF="$OUT.brief"
    { printf 'READ-ONLY SCOUT LANE. Do not create, edit, or delete any file. %s\n' "$WEB_RULE"
      printf 'Answer the brief below directly and completely; label anything not directly observed as INFERRED.\n\n'
      printf '%s\n' "$PROMPT"; } > "$BRIEF"
    ledger seat=scout lane="$LANE" mode="$MODE" engine="$ENGINE" dir="$DIR" state=start
    case "$ENGINE" in
      codex)
        ( cd "$DIR" && codex exec --skip-git-repo-check -s read-only \
            -c approval_policy="never" \
            -c model_reasoning_effort="${SYMPHONY_SCOUT_EFFORT:-medium}" \
            --json -o "$OUT" - < "$BRIEF" ) > "$OUT.jsonl" 2>"$OUT.err" || true
        ;;
      *) echo "bad SYMPHONY_SCOUT_ENGINE: $ENGINE (codex)" >&2; exit 2 ;;
    esac
    if [ ! -s "$OUT" ] || [ "$(tr -d '[:space:][:cntrl:]' < "$OUT" | wc -c)" -eq 0 ]; then
      ledger seat=scout lane="$LANE" engine="$ENGINE" state=fail reason=empty-output out="$OUT"
      echo "scout lane '$LANE' FAILED: $ENGINE returned empty output (a silent exit is a failed lane) — $OUT" >&2
      exit 1
    fi
    ledger seat=scout lane="$LANE" state=done mode="$MODE" engine="$ENGINE" out="$OUT"
    echo "scout lane '$LANE' done ($ENGINE) — answer: $OUT"
    echo "CONDUCTOR: spot-check one load-bearing claim against its source before acting."
    ;;
  *) echo "unknown seat: $SEAT (builder|scout)" >&2; exit 2 ;;
esac
