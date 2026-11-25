#!/usr/bin/env python3
"""Display run metadata or record conductor acceptance without reading private briefs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from symphony_records import (
    append_record,
    decode_json,
    ledger_path,
    runs_directory,
    write_atomic_json,
)

DISPLAY_FIELDS = (
    "run_id", "at", "engine", "seat", "lane", "state", "route",
    "requested_model", "requested_effort", "fast",
    "resolved_model", "resolved_effort",
    "reported_model", "reported_effort", "elapsed_seconds", "routing_elapsed_seconds",
    "usage", "attempt", "exit", "interruption", "denied_actions",
    "scope_control", "extra_args", "route_evidence",
    "acceptance", "frontier_review", "acceptance_note", "out",
)


def normalize_row(row):
    display = {key: row.get(key) for key in DISPLAY_FIELDS}
    # Preserve historical ledger readability; absent telemetry stays null.
    if display["resolved_effort"] is None:
        display["resolved_effort"] = row.get("tier")
    if display["engine"] is None and display["route"] == "codex-cli":
        display["engine"] = "codex"
    return display


def read_ledger_rows(path):
    entries = []
    index_by_run = {}
    with path.open("rb") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                row = decode_json(line)
                if not isinstance(row, dict):
                    raise ValueError("not an object")
            except ValueError:
                print("Unparseable ledger row (possibly an interrupted write)", file=sys.stderr)
                continue
            normalized = normalize_row(row)
            run_id = normalized.get("run_id") or normalized.get("out")
            if isinstance(run_id, str) and run_id in index_by_run:
                entries[index_by_run[run_id]] = normalized
            else:
                if isinstance(run_id, str):
                    index_by_run[run_id] = len(entries)
                entries.append(normalized)
    return entries


def print_table(rows):
    if not rows:
        print("No matching runs.")
        return
    header = f"{'RUN_ID':28} {'SEAT':8} {'ENGINE':7} {'STATE':9} {'ACCEPTANCE':10} {'REVIEW':9} {'ELAPSED':8} {'MODEL':24} {'LANE'}"
    print(header)
    for row in rows:
        run_id = str(row.get("run_id") or Path(row["out"]).parent.name if row.get("out") else "-")[:28]
        seat = str(row.get("seat") or "-")[:8]
        engine = str(row.get("engine") or "-")[:7]
        state = str(row.get("state") or "-")[:9]
        acc = str(row.get("acceptance") or "-")[:10]
        rev = str(row.get("frontier_review") or "-")[:9]
        elapsed = f"{row['elapsed_seconds']:.1f}s" if isinstance(row.get("elapsed_seconds"), (int, float)) else "-"
        model = str(row.get("reported_model") or row.get("resolved_model") or "-")[:24]
        lane = str(row.get("lane") or "-")
        print(f"{run_id:28} {seat:8} {engine:7} {state:9} {acc:10} {rev:9} {elapsed:8} {model:24} {lane}")


def print_summary(rows):
    by_state = Counter(str(r.get("state") or "unknown") for r in rows)
    by_engine = Counter(str(r.get("engine") or "unknown") for r in rows)
    by_acceptance = Counter(str(r.get("acceptance") or "unknown") for r in rows)
    total_elapsed = sum(r["elapsed_seconds"] for r in rows if isinstance(r.get("elapsed_seconds"), (int, float)))
    print(json.dumps({
        "total_runs": len(rows),
        "by_state": dict(sorted(by_state.items())),
        "by_engine": dict(sorted(by_engine.items())),
        "by_acceptance": dict(sorted(by_acceptance.items())),
        "total_elapsed_seconds": round(total_elapsed, 3),
    }, indent=2))


def resolve_result_path(target):
    candidate = Path(target).expanduser()
    if candidate.is_dir():
        candidate = candidate / "result.json"
    elif candidate.exists() and candidate.name == "result.json":
        pass
    elif not candidate.exists():
        by_id = runs_directory() / target / "result.json"
        if by_id.is_file():
            candidate = by_id
    resolved = candidate.resolve(strict=True)
    if resolved.name != "result.json" or not resolved.is_file():
        raise ValueError(f"Expected a Symphony attempt directory, run_id, or result.json path: {target}")
    return resolved


def cmd_mark(args):
    result_path = resolve_result_path(args.target)
    row = decode_json(result_path.read_text(encoding="utf-8"))
    if not isinstance(row, dict) or "state" not in row:
        raise ValueError(f"Malformed result record: {result_path}")
    if args.acceptance == "accepted" and row.get("state") in ("failed", "started"):
        raise ValueError(f"Cannot mark a {row.get('state')} attempt accepted; resolve or repair it first")
    row["acceptance"] = args.acceptance
    if args.review is not None:
        row["frontier_review"] = args.review
    if args.note is not None:
        row["acceptance_note"] = args.note
    row["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    write_atomic_json(result_path, row)
    append_record(row)
    print(json.dumps({
        "run_id": row.get("run_id", result_path.parent.name),
        "lane": row.get("lane"),
        "state": row.get("state"),
        "acceptance": row.get("acceptance"),
        "frontier_review": row.get("frontier_review"),
        "result": str(result_path),
    }))
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "mark":
        parser = argparse.ArgumentParser(prog="symphony-status.sh mark", description="Record conductor acceptance for an attempt.")
        parser.add_argument("target", help="Attempt directory, run_id, or path to result.json")
        parser.add_argument("--acceptance", required=True, choices=("accepted", "rejected", "pending"))
        parser.add_argument("--review", choices=("completed", "pending", "failed"), help="Update frontier_review state")
        parser.add_argument("--note", help="Short evidence/review note (avoid sensitive brief text)")
        return cmd_mark(parser.parse_args(sys.argv[2:]))

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("count", nargs="?", type=int, default=12)
    parser.add_argument("--table", action="store_true", help="Compact human-readable summary table")
    parser.add_argument("--summary", action="store_true", help="Aggregate JSON counts across matching runs")
    parser.add_argument("--lane", help="Filter runs by lane name")
    parser.add_argument("--failed", action="store_true", help="Filter to failed or partial runs")
    args = parser.parse_args()
    if not 1 <= args.count <= 1000:
        parser.error("count must be between 1 and 1000")
    path = ledger_path()
    if not path.exists():
        print(f"No ledger at {path}")
        return 0
    rows = read_ledger_rows(path)
    if args.lane:
        rows = [row for row in rows if row.get("lane") == args.lane]
    if args.failed:
        rows = [row for row in rows if row.get("state") in ("failed", "partial")]
    rows = rows[-args.count:]
    if args.summary:
        print_summary(rows)
    elif args.table:
        print_table(rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(f"symphony: {error}", file=sys.stderr)
        sys.exit(2)
