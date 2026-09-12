"""Read the public Codex model catalog; never start a thread or inference turn."""

import json
from contextlib import suppress
import os
import selectors
import shutil
import subprocess
import sys
import tempfile
import time

from symphony_records import decode_json


class CatalogError(ValueError):
    pass


def discover(binary, cwd):
    """Bounded stdio RPC session using initialize, initialized and model/list only."""
    deadline = time.monotonic() + 30
    buffer = bytearray()
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(
            [binary, "app-server", "--listen", "stdio://"], cwd=cwd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors,
        )
        print(f"catalog_pid={process.pid}", file=sys.stderr)
        selector = selectors.DefaultSelector()

        def send(message):
            process.stdin.write((json.dumps(message) + "\n").encode())
            process.stdin.flush()

        def request(identifier, method, params):
            send({"id": identifier, "method": method, "params": params})
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CatalogError("Model discovery exceeded its 30-second budget")
                if b"\n" not in buffer:
                    if not selector.select(remaining):
                        raise CatalogError("Model discovery timed out")
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        raise CatalogError("Model discovery closed before a response")
                    buffer.extend(chunk)
                    if len(buffer) > 8 * 1024 * 1024:
                        raise CatalogError("Model discovery response exceeds 8 MiB")
                    continue
                line, _, rest = buffer.partition(b"\n")
                buffer[:] = rest
                try:
                    message = decode_json(line)
                except (ValueError, UnicodeError) as error:
                    raise CatalogError("Malformed model discovery response") from error
                if not isinstance(message, dict):
                    raise CatalogError("Unexpected model discovery response")
                if "method" in message and "id" in message:
                    raise CatalogError("Discovery unexpectedly requested client action")
                if message.get("id") != identifier:
                    continue
                if "error" in message or not isinstance(message.get("result"), dict):
                    raise CatalogError("Model discovery rejected the request; check host access/interfaces")
                return message["result"]

        try:
            selector.register(process.stdout, selectors.EVENT_READ)
            request(1, "initialize", {"clientInfo": {"name": "symphony_catalog", "version": "1.0.0"}})
            send({"method": "initialized", "params": {}})
            models, cursors, identifiers = [], set(), set()
            cursor = None
            for page in range(100):
                params = {"limit": 100, "includeHidden": False}
                if cursor is not None:
                    params["cursor"] = cursor
                result = request(page + 2, "model/list", params)
                rows = result.get("data")
                if not isinstance(rows, list):
                    raise CatalogError("Model catalog has no data array")
                for row in rows:
                    if not isinstance(row, dict) or not isinstance(row.get("model"), str) or not row["model"]:
                        raise CatalogError("Model catalog contains an invalid model identifier")
                    if row.get("hidden") is True:
                        continue
                    if row["model"] in identifiers:
                        raise CatalogError("Model catalog contains duplicate identifiers")
                    identifiers.add(row["model"])
                    models.append(row)
                cursor = result.get("nextCursor")
                if cursor is None:
                    if not models:
                        raise CatalogError("No visible models are available")
                    return models
                if not isinstance(cursor, str) or not cursor or cursor in cursors:
                    raise CatalogError("Invalid or repeated model catalog cursor")
                cursors.add(cursor)
            raise CatalogError("Model catalog exceeds 100 pages; no partial catalog accepted")
        finally:
            selector.close()
            # A closed server pipe must not prevent reaping our own process.
            with suppress(OSError):
                process.stdin.close()
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdout.close()
            errors.seek(0)
            shutil.copyfileobj(errors, sys.stderr.buffer)
            sys.stderr.flush()


def select(models, requested_model, requested_effort):
    if requested_model is not None:
        matches = [row for row in models if row["model"] == requested_model]
    else:
        matches = [row for row in models if row.get("isDefault") is True]
    if len(matches) != 1:
        raise CatalogError("Requested model unavailable, or no unique default; select an ID from live discovery")
    model = matches[0]
    options = model.get("supportedReasoningEfforts")
    if not isinstance(options, list) or not options:
        raise CatalogError("Model does not expose supported efforts; choose a compatible host/model explicitly")
    efforts = {}
    for option in options:
        if not isinstance(option, dict) or not isinstance(option.get("reasoningEffort"), str):
            raise CatalogError("Malformed supported reasoning efforts")
        value = option["reasoningEffort"]
        if not value or value in efforts:
            raise CatalogError("Empty or duplicate reasoning effort")
        efforts[value] = option
    effort = model.get("defaultReasoningEffort") if requested_effort == "auto" else requested_effort
    if not isinstance(effort, str) or effort not in efforts:
        raise CatalogError("Requested/default effort is not supported by the selected model")
    # Special execution modes are never inferred from a larger ordinal or model name.
    description = str(efforts[effort].get("description", "")).lower()
    nested = effort.lower() == "ultra" or any(word in description for word in ("delegat", "subagent", "sub-agent"))
    if requested_effort == "auto" and nested:
        raise CatalogError("Default effort may delegate; choose an explicit non-delegating effort")
    return model, effort, nested
