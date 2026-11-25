"""Private, locked run records. Execution and conductor acceptance stay separate."""
import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile


def _canonicalize_directory(path):
    raw = Path(path).expanduser().absolute()
    if os.path.lexists(raw) and raw.is_symlink():
        raise ValueError(f"Use a canonical directory without a symlink leaf: {raw}")
    missing_parts = []
    cur = raw
    while not os.path.lexists(cur) and cur != cur.parent:
        missing_parts.append(cur.name)
        cur = cur.parent
    if missing_parts and cur.is_symlink():
        # Resolve OS/parent symlinks (for example macOS /tmp -> /private/tmp) above missing leaf dirs.
        resolved = cur.resolve()
        for part in reversed(missing_parts):
            resolved = resolved / part
        return resolved
    return raw.resolve() if cur == raw else raw


def owned_directory(path):
    path = _canonicalize_directory(path)
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


def runs_directory():
    return Path(os.environ.get("SYMPHONY_OUT", str(Path.home() / ".symphony/runs"))).expanduser().absolute()


def ledger_path():
    return Path(os.environ.get("SYMPHONY_LEDGER", str(runs_directory() / "ledger.jsonl"))).expanduser().absolute()


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


def write_atomic_json(path, value):
    target = Path(path)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    tmp = Path(tmp_name)
    try:
        os.chmod(tmp, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=True, allow_nan=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
    except Exception:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def reject_constant(value):
    raise ValueError(f"Non-JSON numeric constant: {value}")


def decode_json(data):
    return json.loads(data, parse_constant=reject_constant)


def validate_report(result):
    """The lane report contract; anything else is treated as no report at all."""
    if not isinstance(result, dict) or set(result) != {"status", "summary", "files", "evidence", "not_run"}:
        return None
    if result["status"] not in ("completed", "partial", "failed") or not isinstance(result["summary"], str) or not result["summary"].strip():
        return None
    for key in ("files", "evidence", "not_run"):
        if not isinstance(result[key], list) or not all(isinstance(item, str) for item in result[key]):
            return None
    return result


def inspect_report(path):
    try:
        if Path(path).stat().st_size > 8 * 1024 * 1024:
            return None
        return validate_report(decode_json(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None
