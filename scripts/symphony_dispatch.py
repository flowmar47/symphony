#!/usr/bin/env python3
"""Run one bounded lane on one engine. Selection is explicit; completion never implies acceptance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid

from symphony_engines import (
    ARGV_BRIEF_LIMIT,
    ENGINES,
    EngineError,
    REPORT_CONTRACT,
    check_extra_args,
    engine_named,
)
from symphony_records import (
    append_record,
    decode_json,
    inspect_report,
    private_directory,
    runs_directory,
    write_new,
)
from symphony_seatplan import load_plan, plan_path

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / "lane-result.schema.json"


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    builder = commands.add_parser("builder", help="Writable lane inside one directory")
    builder.add_argument("tier", help="Supported effort value, or auto")
    builder.add_argument("spec")
    scout = commands.add_parser("scout", help="Read-only lane: ask (repository only) or plan (web permitted)")
    scout.add_argument("mode", choices=("ask", "plan"))
    scout.add_argument("prompt", help="Brief text, or @file (preferred for private briefs)")
    for sub in (builder, scout):
        sub.add_argument("directory")
        sub.add_argument("lane")
        sub.add_argument("--seat", help="Resolve defaults from a confirmed seat name in ~/.symphony/seat-plan.json")
    repair = commands.add_parser("resume", help="One repair from an earlier result.json")
    repair.add_argument("previous")
    repair.add_argument("fix_file")
    for sub in (builder, scout, repair):
        sub.add_argument("--engine", choices=sorted(ENGINES), help="codex, agy, cursor or claude (default: seat, env, or codex)")
        sub.add_argument("--model")
        sub.add_argument("--effort", help="Exact supported effort, or auto where the engine has a default")
        fast_group = sub.add_mutually_exclusive_group()
        fast_group.add_argument("--fast", action="store_true", help="Select the engine's fast variant where listed")
        fast_group.add_argument("--no-fast", action="store_true", help="Disable fast variant (overrides seat plan or resume)")
        sub.add_argument("--extra-arg", action="append", default=[],
                         help="One verbatim engine flag, written --extra-arg=--flag (repeatable); scope and approval flags are refused")
        sub.add_argument("--dry-run", action="store_true", help="Discover and print; never launch a lane")
        sub.add_argument("--max-seconds", type=int, default=480)
        sub.add_argument("--allow-nested-delegation", action="store_true",
                         help="Attest explicit nested-delegation authority and a compatible host resource budget")
    return parser.parse_args()


def read_brief(path):
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Brief must be a regular UTF-8 file no larger than 1 MiB")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("Brief is empty")
    return text


def seat_route(seat_name):
    plan_file = plan_path()
    plan = load_plan(plan_file)
    if plan is None:
        raise ValueError(f"No confirmed seat plan at {plan_file}; save one with symphony-seat-plan.sh save")
    route = plan["seats"].get(seat_name)
    if route is None:
        raise ValueError(f"Seat {seat_name!r} is not in {plan_file}; available: {sorted(plan['seats'])}")
    if route["engine"] == "native":
        raise ValueError(f"Seat {seat_name!r} uses engine 'native'; dispatch it with the host tool, not CLI")
    return route


def previous_attempt(args):
    path = Path(args.previous).expanduser().resolve(strict=True)
    previous = decode_json(path.read_text(encoding="utf-8"))
    if not isinstance(previous, dict) or previous.get("attempt") != 1 or previous.get("state") not in ("failed", "partial", "completed"):
        raise ValueError("Repair requires an original completed/partial/failed Symphony result")
    if path.name != "result.json" or previous.get("run_id") != path.parent.name or previous.get("out") != str(path.parent / "report.json"):
        raise ValueError("Repair result must remain in its original attempt directory")
    if (path.parent / "repair-claimed.json").exists():
        raise ValueError("This attempt has already claimed its one permitted repair")
    request = decode_json((path.parent / "request.json").read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("Original request.json is missing or invalid")
    if previous.get("engine") is None and previous.get("route") == "codex-cli":
        previous = {**previous, "engine": "codex"}
        if request.get("engine") is None:
            request = {**request, "engine": "codex"}
    for key in ("engine", "seat", "directory", "lane", "sandbox", "mode", "attempt", "resolved_model", "resolved_effort", "fast", "brief_sha256"):
        if previous.get(key) != request.get(key):
            raise ValueError("Repair result disagrees with the original request's scope or route")
    return path, previous


def job_for(args):
    previous = None
    seat_defaults = seat_route(args.seat) if getattr(args, "seat", None) else None
    engine_name = args.engine
    fast_override = True if args.fast else (False if args.no_fast else None)
    if args.command == "resume":
        path, previous = previous_attempt(args)
        if engine_name not in (None, previous["engine"]):
            raise ValueError("A repair stays on the original engine")
        engine_name = previous["engine"]
        job = {key: previous[key] for key in ("engine", "seat", "directory", "lane", "sandbox", "mode")}
        job.update(attempt=2, retry_of=str(path), thread=None)
        fix = read_brief(args.fix_file)
        if engine_name == "codex":
            if not isinstance(previous.get("thread"), str):
                raise ValueError("Original result has no resumable thread ID")
            job["thread"] = str(uuid.UUID(previous["thread"]))
            brief = fix
        else:
            # Engines without a driven resume get the original spec plus the fix list in a fresh lane.
            spec = path.parent / "spec.txt"
            if not spec.is_file():
                raise ValueError("Original attempt has no spec.txt; only attempts made by this version can be repaired")
            brief = spec.read_text(encoding="utf-8") + "\n\nREPAIR ATTEMPT (the one permitted): address exactly this fix list.\n" + fix
    else:
        seat = args.command
        if engine_name is None:
            engine_name = (
                seat_defaults["engine"]
                if seat_defaults
                else os.environ.get(f"SYMPHONY_{seat.upper()}_ENGINE", os.environ.get("SYMPHONY_ENGINE", "codex"))
            )
        job = {"engine": engine_name, "seat": seat, "directory": args.directory, "lane": args.lane,
               "sandbox": "workspace-write" if seat == "builder" else "read-only",
               "mode": args.mode if seat == "scout" else None,
               "attempt": 1, "retry_of": None, "thread": None}
        if args.seat:
            job["confirmed_seat"] = args.seat
        if seat == "builder":
            brief = read_brief(args.spec)
        else:
            brief = read_brief(args.prompt[1:]) if args.prompt.startswith("@") else args.prompt
    engine = engine_named(job["engine"])
    if job["seat"] not in ("builder", "scout"):
        raise ValueError("Invalid original role")
    required = "workspace-write" if job["seat"] == "builder" else "read-only"
    if job["sandbox"] != required or (job["seat"] == "scout" and job["mode"] not in ("ask", "plan")):
        raise ValueError("Original permissions/mode do not match the role")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", job["lane"]):
        raise ValueError("Lane must be 1–64 ASCII letters, digits, underscores or hyphens")
    directory = Path(job["directory"]).expanduser().resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("Working directory does not exist")
    job["directory"] = str(directory)
    if not brief.strip() or len(brief.encode("utf-8")) > 1024 * 1024:
        raise ValueError("Brief must contain 1 byte to 1 MiB of UTF-8 text")
    if not 1 <= args.max_seconds <= 86400:
        raise ValueError("Time budget must be between 1 and 86400 seconds")
    check_extra_args(job["seat"], args.extra_arg, engine=engine.name)
    prefix = "Implement the bounded spec. Stop on a false premise; do not redesign or silently weaken requirements."
    if job["seat"] == "scout":
        prefix = "READ-ONLY SCOUT. Do not create, edit or delete files. "
        prefix += ("Use authorized web research and cite load-bearing sources." if job["mode"] == "plan"
                   else "Do not use web search/fetch. Answer from the supplied repository; label unobserved claims.")
    if previous:
        prefix += " This is the one permitted repair attempt. Preserve the original scope and constraints."
    prompt = (prefix + "\nNo commits, pushes, publication or release actions: the conductor alone lands.\n"
              "No further delegation unless explicitly authorized with a compatible resource budget.\n"
              "Report completed, partial or failed honestly. List evidence paths and checks NOT RUN.\n\n" + brief)
    if engine.prompt_via == "argv":
        argv_overhead = "" if engine.name == "claude" else f"WORKING DIRECTORY: {job['directory']}\n\n" + REPORT_CONTRACT
        argv_bytes = len((prompt + argv_overhead).encode("utf-8"))
        if argv_bytes > ARGV_BRIEF_LIMIT:
            raise ValueError(f"{engine.name} receives the full prompt as an argument ({argv_bytes} bytes > {ARGV_BRIEF_LIMIT // 1024} KiB); shorten it or point it at a file")
    requested_model = args.model
    requested_effort = args.effort
    if previous:
        if requested_model is None:
            # Composite IDs (cursor/agy) resolve from the base model the original request named.
            requested_model = previous["resolved_model"] if job["engine"] == "codex" else (previous.get("requested_model") or previous["resolved_model"])
        if requested_effort is None:
            requested_effort = previous.get("resolved_effort") or previous.get("tier")
        fast = bool(previous.get("fast")) if fast_override is None else fast_override
    else:
        if requested_model is None:
            requested_model = (
                seat_defaults["model"]
                if seat_defaults
                else os.environ.get(f"SYMPHONY_{job['seat'].upper()}_MODEL", os.environ.get("SYMPHONY_MODEL"))
            )
        if requested_effort is None:
            if args.seat and seat_defaults:
                requested_effort = seat_defaults["effort"] if (job["seat"] == "scout" or args.tier == "auto") else args.tier
            else:
                requested_effort = args.tier if job["seat"] == "builder" else os.environ.get("SYMPHONY_SCOUT_EFFORT", "auto")
        if fast_override is not None:
            fast = fast_override
        elif seat_defaults:
            fast = bool(seat_defaults.get("fast", False))
        else:
            fast = False
    job.update(requested_model=requested_model, requested_effort=requested_effort, fast=fast,
               extra_args=list(args.extra_arg), max_seconds=args.max_seconds,
               scope_control=engine.scope_control[job["seat"]],
               brief_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest())
    return engine, job, prompt, brief


def stop_owned_group(process):
    # Only the new session/group started by this invocation is signalled.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def wait_for_lane(process, max_seconds):
    try:
        return process.wait(timeout=max_seconds), None
    except subprocess.TimeoutExpired:
        stop_owned_group(process)
        return process.returncode, "timeout"


def run(args):
    os.umask(0o077)
    routing_started = time.monotonic()
    engine, job, prompt, brief = job_for(args)
    models = engine.discover(job["directory"])
    try:
        model, effort, nested = engine.resolve(models, job["requested_model"], job["requested_effort"], job["fast"])
    except EngineError as error:
        raise ValueError(f"{engine.name}: {error}") from error
    if nested and not args.allow_nested_delegation:
        raise ValueError("This effort may delegate; explicit authority/resource acknowledgement is required")
    verified = getattr(engine, "verified", lambda requested: True)(job["requested_model"])
    job.update(resolved_model=model, resolved_effort=effort, route=f"{engine.name}-cli",
               route_evidence="provisional" if verified else "unverified-id", acceptance="pending",
               frontier_review="pending", routing_elapsed_seconds=round(time.monotonic() - routing_started, 3))
    if args.dry_run:
        placeholder = Path("<private-attempt>")
        command = engine.command(job, placeholder, "<brief>", SCHEMA)
        print(json.dumps({**job, "dry_run": True, "command": command, "stdin": engine.prompt_via}, indent=2))
        return 0
    base = private_directory(runs_directory())
    attempt = Path(tempfile.mkdtemp(prefix=job["lane"] + "-", dir=base))
    job.update(at=str(datetime.now(timezone.utc).isoformat()), run_id=attempt.name,
               out=str(attempt / "report.json"), state="started", pid=None)
    write_new(attempt / "catalog.json", {"engine": engine.name, "models": models})
    (attempt / "spec.txt").write_text(brief, encoding="utf-8")
    (attempt / "brief.txt").write_text(prompt, encoding="utf-8")
    write_new(attempt / "request.json", job)
    append_record(job)
    started = time.monotonic()
    process = None
    interrupted = None
    exit_code = None
    redacted_command = engine.command(job, attempt, "<brief-in-brief.txt>", SCHEMA)
    try:
        if job["retry_of"]:
            # An exclusive marker prevents two concurrent repairs of one attempt.
            marker = Path(job["retry_of"]).parent / "repair-claimed.json"
            write_new(marker, {"repair": str(attempt), "at": job["at"]})
        command = engine.command(job, attempt, prompt, SCHEMA)
        with (attempt / "events.jsonl").open("xb") as events, (attempt / "stderr.log").open("xb") as errors:
            stdin = (attempt / "brief.txt").open("rb") if engine.prompt_via == "stdin" else subprocess.DEVNULL
            try:
                process = subprocess.Popen(command, cwd=job["directory"], stdin=stdin, stdout=events,
                                           stderr=errors, start_new_session=True, env=engine.environment())
            finally:
                if stdin is not subprocess.DEVNULL:
                    stdin.close()
            job["pid"] = process.pid
            write_new(attempt / "process.json", {"command": redacted_command, "stdin": engine.prompt_via, "pid": process.pid})
            print(f"lane_pid={process.pid} engine={engine.name} attempt={attempt}", flush=True)
            try:
                exit_code, interrupted = wait_for_lane(process, args.max_seconds)
            except KeyboardInterrupt:
                interrupted = "interrupted"
                stop_owned_group(process)
                exit_code = process.returncode
    except (OSError, ValueError, KeyboardInterrupt) as error:
        interrupted = "interrupted" if isinstance(error, KeyboardInterrupt) else type(error).__name__
        if process is not None and process.poll() is None:
            stop_owned_group(process)
        if process is not None:
            exit_code = process.returncode
        if not (attempt / "process.json").exists():
            try:
                write_new(attempt / "process.json", {"command": redacted_command, "stdin": engine.prompt_via, "pid": job["pid"]})
            except OSError:
                pass
    try:
        inspection = engine.inspect(attempt)
    except (OSError, ValueError):
        inspection = {"event_error": True, "terminal": None, "usage": None, "response": None,
                      "thread": None, "reported_model": None, "reported_effort": None}
    report = None
    if not interrupted and inspection.get("terminal") == "completed":
        derived = engine.report_from(inspection, attempt)
        if derived is not None:
            try:
                write_new(attempt / "report.json", derived)
            except OSError:
                pass
        report = inspect_report(attempt / "report.json")
    successful = (exit_code == 0 and inspection.get("terminal") == "completed"
                  and not inspection.get("event_error") and report is not None and not interrupted)
    state = report["status"] if successful else "failed"
    if state == "completed" and report["not_run"]:
        state = "partial"
    job.update({key: inspection.get(key) for key in ("thread", "terminal", "usage", "reported_model", "reported_effort", "event_error", "denied_actions")})
    job.update(state=state, exit=exit_code, interruption=interrupted,
               elapsed_seconds=round(time.monotonic() - started, 3),
               completed_at=datetime.now(timezone.utc).isoformat())
    write_new(attempt / "result.json", job)
    append_record(job)
    print(f"{state}: {attempt / 'result.json'}; acceptance pending frontier review/evidence inspection")
    if interrupted == "interrupted":
        return 130
    return 0 if state == "completed" else 3 if state == "partial" else 1


def handle_termination(signum, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_termination)
    try:
        sys.exit(run(arguments()))
    except KeyboardInterrupt:
        print("symphony: interrupted before lane completion", file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"symphony: {error}", file=sys.stderr)
        sys.exit(2)
