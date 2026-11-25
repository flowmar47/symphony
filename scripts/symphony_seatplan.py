#!/usr/bin/env python3
"""Keep the last confirmed seat plan and check it against live discovery.

    symphony-seat-plan.sh show                 # print the stored plan (or say there is none)
    symphony-seat-plan.sh check                # every seat: available / unverified / missing / native
    symphony-seat-plan.sh save plan.json       # validate, check, store as the confirmed plan
    symphony-seat-plan.sh save -               # same, plan JSON on stdin

A plan is {"seats": {"<seat>": {"engine": ..., "model": ..., "effort": ..., "fast": bool?}}}.
Engine "native" means the host's own delegation tool; a script cannot verify it, so the
conductor confirms that route in-session. The plan is a starting proposal for the next
invocation's availability question, never an automatic route.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

from symphony_engines import ENGINES, EngineError, discover_all
from symphony_records import decode_json, owned_directory, write_atomic_json

VALID_ENGINES = set(ENGINES) | {"native"}


def plan_path():
    return Path(os.environ.get("SYMPHONY_SEAT_PLAN", str(Path.home() / ".symphony/seat-plan.json"))).expanduser().absolute()


def load_plan(path):
    if not path.is_file():
        return None
    return validate_plan(decode_json(path.read_text(encoding="utf-8")))


def validate_plan(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get("seats"), dict) or not plan["seats"]:
        raise ValueError('A plan is {"seats": {"<seat>": {"engine", "model", "effort", "fast"?}}}')
    for seat, route in plan["seats"].items():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", seat):
            raise ValueError(f"Seat name {seat!r} must be 1–64 ASCII letters, digits, underscores or hyphens")
        if not isinstance(route, dict) or route.get("engine") not in VALID_ENGINES:
            raise ValueError(f"Seat {seat!r} needs an engine from {sorted(VALID_ENGINES)}")
        for key in ("model", "effort"):
            if not isinstance(route.get(key), str) or not route[key]:
                raise ValueError(f"Seat {seat!r} needs a non-empty string {key}")
        if not isinstance(route.get("fast", False), bool):
            raise ValueError(f"Seat {seat!r}: fast must be a boolean")
        extra = set(route) - {"engine", "model", "effort", "fast", "note"}
        if extra:
            raise ValueError(f"Seat {seat!r} has unknown keys {sorted(extra)}")
    return plan


def check_plan(plan, cwd):
    engines = sorted({route["engine"] for route in plan["seats"].values()} - {"native"})
    catalogs = discover_all(cwd, engines) if engines else {}
    verdicts = {}
    for seat, route in plan["seats"].items():
        if route["engine"] == "native":
            verdicts[seat] = {"status": "native", "detail": "host delegation tool; confirm model/effort in-session"}
            continue
        catalog = catalogs[route["engine"]]
        if not catalog["ok"]:
            verdicts[seat] = {"status": "missing", "detail": catalog["error"]}
            continue
        try:
            engine = ENGINES[route["engine"]]
            resolved, effort, nested = engine.resolve(catalog["models"], route["model"], route["effort"], route.get("fast", False))
            verified = getattr(engine, "verified", lambda requested: True)(route["model"])
            verdicts[seat] = {"status": "available" if verified else "unverified",
                              "detail": f"{resolved} effort={effort}" + (" (may delegate)" if nested else "")
                              + ("" if verified else "; full ID not in any catalog, proven only by the served model")}
        except EngineError as error:
            verdicts[seat] = {"status": "missing", "detail": str(error)}
    return verdicts


def print_verdicts(plan, verdicts):
    for seat, route in plan["seats"].items():
        verdict = verdicts[seat]
        fast = " fast" if route.get("fast") else ""
        print(f"{verdict['status']:9} {seat:22} {route['engine']:7} {route['model']} {route['effort']}{fast}  {verdict['detail']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("show")
    commands.add_parser("check")
    save = commands.add_parser("save")
    save.add_argument("source", help="Plan JSON file, or - for stdin")
    args = parser.parse_args()
    path = plan_path()
    if args.command == "show":
        plan = load_plan(path)
        if plan is None:
            print(f"No confirmed seat plan at {path}")
            return 3
        print(json.dumps(plan, indent=2))
        return 0
    if args.command == "check":
        plan = load_plan(path)
        if plan is None:
            print(f"No confirmed seat plan at {path}")
            return 3
        verdicts = check_plan(plan, os.getcwd())
        print_verdicts(plan, verdicts)
        return 0 if all(v["status"] != "missing" for v in verdicts.values()) else 3
    text = sys.stdin.read() if args.source == "-" else Path(args.source).expanduser().read_text(encoding="utf-8")
    plan = validate_plan(decode_json(text))
    verdicts = check_plan(plan, os.getcwd())
    print_verdicts(plan, verdicts)
    if any(v["status"] == "missing" for v in verdicts.values()):
        print("symphony: not saved; every non-native seat must resolve against live discovery", file=sys.stderr)
        return 3
    os.umask(0o077)
    dir_path = owned_directory(path.parent)
    target = dir_path / path.name
    stored = {"confirmed_at": datetime.now(timezone.utc).isoformat(), "seats": plan["seats"]}
    write_atomic_json(target, stored)
    print(f"saved {target}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, ValueError) as error:
        print(f"symphony: {error}", file=sys.stderr)
        sys.exit(2)
