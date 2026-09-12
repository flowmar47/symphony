"""Private, locked run records. Execution and conductor acceptance stay separate."""
import fcntl
import json
import os
from pathlib import Path
import stat


def owned_directory(path):
    path = Path(path).expanduser().absolute()
    if path.resolve() != path:
        raise ValueError(f"Use a canonical directory without symbolic links: {path}")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ValueError(f"An owned directory without group/other write access is required: {path}")
    return path


def private_directory(path):
    path = owned_directory(path)
    if path.stat().st_mode & 0o077:
        raise ValueError(f"A private owner-only directory is required: {path}")
    return path


def ledger_path():
    return Path(os.environ.get("SYMPHONY_LEDGER", str(Path.home() / ".symphony/runs/ledger.jsonl"))).expanduser().absolute()


def append_record(row):
    path = ledger_path()
    private_directory(path.parent)
    fd = os.open(path, os.O_APPEND | os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError("Ledger must be a private single-link regular file")
        fcntl.flock(fd, fcntl.LOCK_EX)
        data = (json.dumps(row, ensure_ascii=True, allow_nan=False) + "\n").encode()
        while data:
            size = os.write(fd, data)
            if size <= 0:
                raise OSError("Ledger write did not progress")
            data = data[size:]
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, allow_nan=False, indent=2)
        stream.write("\n")


def reject_constant(value):
    raise ValueError(f"Non-JSON numeric constant: {value}")


def decode_json(data):
    return json.loads(data, parse_constant=reject_constant)


def inspect_events(path):
    result = {"thread": None, "terminal": None, "usage": None,
              "reported_model": None, "reported_effort": None, "event_error": False}
    with Path(path).open("rb") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                event = decode_json(line)
                if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                    raise ValueError("Invalid event object")
            except ValueError:
                result["event_error"] = True
                continue
            kind = event["type"]
            if kind == "thread.started":
                result["thread"] = event.get("thread_id")
            if kind == "turn.started":
                result["terminal"] = None
            if kind in ("turn.completed", "turn.failed"):
                result["terminal"] = kind
                if kind == "turn.failed":
                    result["event_error"] = True
                if isinstance(event.get("usage"), dict):
                    result["usage"] = event["usage"]
            if kind == "error":
                result["event_error"] = True
            if kind in ("thread.started", "turn.started", "turn.completed"):
                if isinstance(event.get("model"), str):
                    result["reported_model"] = event["model"]
                if isinstance(event.get("reasoning_effort"), str):
                    result["reported_effort"] = event["reasoning_effort"]
            if kind == "model.rerouted" and isinstance(event.get("to_model"), str):
                result["reported_model"] = event["to_model"]
    return result


def inspect_report(path):
    try:
        if Path(path).stat().st_size > 8 * 1024 * 1024:
            return None
        result = decode_json(Path(path).read_text(encoding="utf-8"))
        if not isinstance(result, dict) or set(result) != {"status", "summary", "files", "evidence", "not_run"}:
            return None
        if result["status"] not in ("completed", "partial", "failed") or not isinstance(result["summary"], str) or not result["summary"].strip():
            return None
        for key in ("files", "evidence", "not_run"):
            if not isinstance(result[key], list) or not all(isinstance(item, str) for item in result[key]):
                return None
        return result
    except (OSError, ValueError):
        return None
