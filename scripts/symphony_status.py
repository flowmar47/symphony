#!/usr/bin/env python3
"""Display run metadata without reading briefs or final-answer text."""
import argparse
from collections import deque
import json
import sys

from symphony_records import decode_json, ledger_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("count", nargs="?", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.count <= 1000:
        parser.error("count must be between 1 and 1000")
    path = ledger_path()
    if not path.exists():
        print(f"No ledger at {path}")
        return
    with path.open("rb") as stream:
        rows = deque(stream, maxlen=args.count)
    for line in rows:
        try:
            row = decode_json(line)
            if not isinstance(row, dict):
                raise ValueError("not an object")
            display = {key: row.get(key) for key in (
                "at", "seat", "lane", "state", "route", "requested_model", "requested_effort",
                "resolved_model", "resolved_effort",
                "reported_model", "reported_effort", "elapsed_seconds", "routing_elapsed_seconds", "usage", "attempt",
                "exit", "acceptance", "frontier_review", "out")}
            # Preserve historical ledger readability; absent telemetry stays null.
            if display["resolved_effort"] is None:
                display["resolved_effort"] = row.get("tier")
            print(json.dumps(display, ensure_ascii=True))
        except ValueError:
            print("Unparseable ledger row (possibly an interrupted write)", file=sys.stderr)


if __name__ == "__main__":
    main()
