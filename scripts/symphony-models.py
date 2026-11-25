#!/usr/bin/env python3
"""Print what every installed engine can run right now, without performing inference.

    symphony-models.py                # JSON: {"engines": {name: {ok, binary, models|error}}}
    symphony-models.py --table        # one line per model: engine, model, efforts, notes
    symphony-models.py --engine agy --engine cursor

Codex is read through app-server model/list; agy through `agy models`; Cursor through
`agent --list-models`; Claude Code lists its documented aliases (the served model is only
known after a run). A failed engine is reported in place; it never invents a catalog.
"""
import argparse
from datetime import datetime, timezone
import json
import os
import signal
import sys

from symphony_engines import ENGINES, discover_all


def handle_termination(signum, frame):
    raise KeyboardInterrupt


def public_rows(rows):
    return [{key: value for key, value in row.items() if key not in ("raw", "ids")} for row in rows]


def print_table(report):
    for name in sorted(report):
        engine = report[name]
        if not engine["ok"]:
            print(f"{name:7} UNAVAILABLE  {engine['error']}")
            continue
        for row in engine["models"]:
            notes = []
            if row.get("is_default"):
                notes.append("codex default")
            if row.get("default_effort"):
                notes.append(f"default effort {row['default_effort']}")
            if row.get("fast"):
                notes.append("fast variant")
            if row.get("source"):
                notes.append(row["source"])
            print(f"{name:7} {row['model']:40} {','.join(row['efforts']):40} {'; '.join(notes)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", action="append", choices=sorted(ENGINES), help="Limit discovery (repeatable)")
    parser.add_argument("--table", action="store_true", help="Human-readable lines instead of JSON")
    args = parser.parse_args()
    report = discover_all(os.getcwd(), args.engine)
    for engine in report.values():
        engine["models"] = public_rows(engine["models"])
    if args.table:
        print_table(report)
    else:
        print(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "engines": report}, indent=2))
    return 0 if all(engine["ok"] for engine in report.values()) else 3


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_termination)
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("symphony: discovery interrupted", file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError) as error:
        print(f"symphony: {error}", file=sys.stderr)
        sys.exit(2)
