#!/usr/bin/env python3
"""CLI fallback. Selection is explicit; completion never implies acceptance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

from symphony_catalog import discover, select
from symphony_records import append_record, decode_json, inspect_events, inspect_report, private_directory, write_new

ROOT = Path(__file__).resolve().parent


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    builder = commands.add_parser("builder")
    builder.add_argument("tier", help="Supported effort value, or auto")
    builder.add_argument("spec")
    scout = commands.add_parser("scout")
    scout.add_argument("mode", choices=("ask", "plan"))
    scout.add_argument("prompt", help="Brief text, or @file (preferred for private briefs)")
    for sub in (builder, scout):
        sub.add_argument("directory")
        sub.add_argument("lane")
    repair = commands.add_parser("resume", help="One repair from an earlier result.json")
    repair.add_argument("previous")
    repair.add_argument("fix_file")
    for sub in (builder, scout, repair):
        sub.add_argument("--model")
        sub.add_argument("--effort", help="Exact supported effort, or auto")
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


def job_for(args):
    previous = None
    if args.command == "resume":
        path = Path(args.previous).expanduser().resolve(strict=True)
        previous = decode_json(path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict) or previous.get("attempt") != 1 or previous.get("state") not in ("failed", "partial", "completed"):
            raise ValueError("Repair requires an original completed/partial/failed Symphony result")
        if path.name != "result.json" or previous.get("run_id") != path.parent.name or previous.get("out") != str(path.parent / "report.json"):
            raise ValueError("Repair result must remain in its original attempt directory")
        request = decode_json((path.parent / "request.json").read_text(encoding="utf-8"))
        for key in ("seat", "directory", "lane", "sandbox", "mode", "attempt", "resolved_model", "resolved_effort", "brief_sha256"):
            if not isinstance(request, dict) or previous.get(key) != request.get(key):
                raise ValueError("Repair result disagrees with the original request's scope or route")
        if not isinstance(previous.get("thread"), str):
            raise ValueError("Original result has no resumable thread ID")
        thread = str(uuid.UUID(previous["thread"]))
        job = {key: previous[key] for key in ("seat", "directory", "lane", "sandbox", "mode")}
        job.update(attempt=2, retry_of=str(path), thread=thread)
        brief = read_brief(args.fix_file)
    else:
        seat = args.command
        job = {"seat": seat, "directory": args.directory, "lane": args.lane,
               "sandbox": "workspace-write" if seat == "builder" else "read-only",
               "mode": args.mode if seat == "scout" else None,
               "attempt": 1, "retry_of": None, "thread": None}
        if seat == "builder":
            brief = read_brief(args.spec)
        else:
            brief = read_brief(args.prompt[1:]) if args.prompt.startswith("@") else args.prompt
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
    if not brief.strip() or len(brief.encode()) > 1024 * 1024:
        raise ValueError("Brief must contain 1 byte to 1 MiB of UTF-8 text")
    if not 1 <= args.max_seconds <= 86400:
        raise ValueError("Time budget must be between 1 and 86400 seconds")
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
    requested_model = args.model
    requested_effort = args.effort
    if previous:
        if requested_model is None:
            requested_model = previous["resolved_model"]
        if requested_effort is None:
            requested_effort = previous["resolved_effort"]
    else:
        if requested_model is None:
            requested_model = os.environ.get(f"SYMPHONY_{job['seat'].upper()}_MODEL", os.environ.get("SYMPHONY_MODEL"))
        if requested_effort is None:
            requested_effort = args.tier if job["seat"] == "builder" else os.environ.get("SYMPHONY_SCOUT_EFFORT", "auto")
    job.update(requested_model=requested_model, requested_effort=requested_effort,
               max_seconds=args.max_seconds, brief_sha256=hashlib.sha256(prompt.encode()).hexdigest())
    return job, prompt


def command_for(binary, job, output):
    command = [binary, "exec"]
    if job["retry_of"]:
        command.append("resume")
    command += ["--model", job["resolved_model"],
                "-c", "model_reasoning_effort=" + json.dumps(job["resolved_effort"]),
                "-c", "sandbox_mode=" + json.dumps(job["sandbox"]),
                "-c", 'approval_policy="never"',
                "--json", "--output-schema", str(ROOT / "lane-result.schema.json"),
                "-o", str(output)]
    if job["seat"] == "scout":
        command.append("--skip-git-repo-check")
    if job["retry_of"]:
        command.append(job["thread"])
    command.append("-")
    return command


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


def run(args):
    os.umask(0o077)
    routing_started = time.monotonic()
    job, prompt = job_for(args)
    if os.environ.get("SYMPHONY_SCOUT_ENGINE", "codex") != "codex" and job["seat"] == "scout":
        raise ValueError("CLI fallback supports the installed codex engine only")
    binary = shutil.which("codex")
    if not binary:
        raise ValueError("codex is not on PATH")
    models = discover(binary, job["directory"])
    model, effort, nested = select(models, job["requested_model"], job["requested_effort"])
    if nested and not args.allow_nested_delegation:
        raise ValueError("This effort may delegate; explicit authority/resource acknowledgement is required")
    job.update(resolved_model=model["model"], resolved_effort=effort, route="codex-cli",
               route_evidence="provisional", acceptance="pending", frontier_review="pending",
               routing_elapsed_seconds=round(time.monotonic() - routing_started, 3))
    if args.dry_run:
        print(json.dumps({**job, "dry_run": True,
                          "command": command_for(binary, job, "<private-attempt>/report.json")}, indent=2))
        return 0
    base = private_directory(os.environ.get("SYMPHONY_OUT", str(Path.home() / ".symphony/runs")))
    attempt = Path(tempfile.mkdtemp(prefix=job["lane"] + "-", dir=base))
    job.update(at=str(datetime.now(timezone.utc).isoformat()), run_id=attempt.name,
               out=str(attempt / "report.json"), state="started", pid=None)
    write_new(attempt / "catalog.json", {"source": "model/list", "models": models})
    (attempt / "brief.txt").write_text(prompt, encoding="utf-8")
    write_new(attempt / "request.json", job)
    append_record(job)
    started = time.monotonic()
    process = None
    interrupted = None
    exit_code = None
    try:
        if job["retry_of"]:
            # An exclusive marker prevents two concurrent resumes of one attempt.
            marker = Path(job["retry_of"]).parent / "repair-claimed.json"
            write_new(marker, {"repair": str(attempt), "at": job["at"]})
        with (attempt / "brief.txt").open("rb") as source, (attempt / "events.jsonl").open("xb") as events, (attempt / "stderr.log").open("xb") as errors:
            process = subprocess.Popen(command_for(binary, job, attempt / "report.json"),
                                       cwd=job["directory"], stdin=source, stdout=events,
                                       stderr=errors, start_new_session=True)
            job["pid"] = process.pid
            write_new(attempt / "process.json", {"pid": process.pid, "command": command_for(binary, job, attempt / "report.json")})
            print(f"lane_pid={process.pid} attempt={attempt}", flush=True)
            try:
                exit_code = process.wait(timeout=args.max_seconds)
            except subprocess.TimeoutExpired:
                interrupted = "timeout"
                stop_owned_group(process)
                exit_code = process.returncode
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
    try:
        event = inspect_events(attempt / "events.jsonl")
    except (OSError, ValueError):
        event = {"event_error": True, "terminal": None, "usage": None}
    report = inspect_report(attempt / "report.json")
    successful = exit_code == 0 and event.get("terminal") == "turn.completed" and not event.get("event_error") and report is not None and not interrupted
    state = report["status"] if successful else "failed"
    if state == "completed" and report["not_run"]:
        state = "partial"
    job.update(event)
    job.update(state=state, exit=exit_code, interruption=interrupted,
               elapsed_seconds=round(time.monotonic() - started, 3),
               completed_at=datetime.now(timezone.utc).isoformat())
    write_new(attempt / "result.json", job)
    append_record(job)
    print(f"{state}: {attempt / 'result.json'}; acceptance pending frontier review/evidence inspection")
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
