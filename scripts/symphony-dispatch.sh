#!/bin/bash
# symphony-dispatch.sh — one entry point for delegating a lane to a seat.
#
#   symphony-dispatch.sh builder <medium|high|max> <spec.md> <repo-dir> <lane-name>
#   symphony-dispatch.sh scout   <ask|plan>        <prompt|@file> <dir> <lane-name>
#
# builder: runs Codex CLI headless (workspace-write, approvals off) against a frozen
#          spec; report lands in $SYMPHONY_OUT/<lane>.txt, thread id in the ledger.
# scout:   runs cursor-agent read-only (ask = repo Q&A, plan = +web research) with
#          cursor-grok-4.6-xhigh-fast; answer lands in $SYMPHONY_OUT/<lane>.txt.
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
    case "$MODE" in
      ask)  FLAGS=(--mode ask) ;;
      plan) FLAGS=(--mode plan --force) ;;   # plan+force enables web tools, still no edits
      *) echo "bad mode: $MODE" >&2; exit 2 ;;
    esac
    [ "${PROMPT#@}" != "$PROMPT" ] && PROMPT="$(cat "${PROMPT#@}")"
    OUT="$SYMPHONY_OUT/$LANE.txt"
    ledger seat=scout lane="$LANE" mode="$MODE" dir="$DIR" state=start
    ( cd "$DIR" && cursor-agent -p --trust "${FLAGS[@]}" \
        --model "${SYMPHONY_SCOUT_MODEL:-cursor-grok-4.6-xhigh-fast}" \
        --output-format text "$PROMPT" ) > "$OUT" 2>&1 \
      || { ledger seat=scout lane="$LANE" state=fail exit=$?; echo "scout failed — $OUT" >&2; exit 1; }
    ledger seat=scout lane="$LANE" state=done mode="$MODE" out="$OUT"
    echo "scout lane '$LANE' done — answer: $OUT"
    echo "CONDUCTOR: spot-check one load-bearing claim against its source before acting."
    ;;
  *) echo "unknown seat: $SEAT (builder|scout)" >&2; exit 2 ;;
esac
