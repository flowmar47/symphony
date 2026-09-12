#!/usr/bin/env python3
"""Print the current public model/list response without performing inference."""
import json
import os
import shutil
import signal
import sys

from symphony_catalog import CatalogError, discover


def handle_termination(signum, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_termination)
    try:
        binary = shutil.which("codex")
        if binary is None:
            raise CatalogError("codex is not on PATH")
        print(json.dumps({"source": "codex app-server model/list", "models": discover(binary, os.getcwd())}, indent=2))
    except KeyboardInterrupt:
        print("symphony: discovery interrupted", file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError) as error:
        print(f"symphony: {error}", file=sys.stderr)
        sys.exit(2)
