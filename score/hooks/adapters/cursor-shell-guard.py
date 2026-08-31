#!/usr/bin/env python3
"""Cursor beforeShellExecution adapter for Score pre-tool-guard.

Translates Cursor stdin ({command,cwd,...}) into the Claude Bash shape the shared
guard expects, then emits Cursor-native permission JSON. Fail-open on any error.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "pre-tool-guard.py"

# Soft gate: ask the user instead of hard-deny (Cursor permission:ask).
ASK_PATTERNS = [
    re.compile(r"\bgit\s+(rebase|filter-branch|filter-repo)\b"),
    re.compile(r"\bgit\s+commit\b[^|;&]*--amend"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
]


def allow(msg: str | None = None) -> None:
    out: dict = {"permission": "allow"}
    if msg:
        out["agent_message"] = msg
    print(json.dumps(out))
    sys.exit(0)


def ask(reason: str) -> None:
    print(
        json.dumps(
            {
                "permission": "ask",
                "user_message": f"Score risk-guard: {reason}",
                "agent_message": (
                    f"BLOCKED pending approval: {reason}. "
                    "Ask the user to approve, or narrow the command."
                ),
            }
        )
    )
    sys.exit(0)


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "permission": "deny",
                "user_message": f"Score risk-guard denied: {reason}",
                "agent_message": (
                    f"BLOCKED by Score risk-guard: {reason}. "
                    "If truly intended, ask the user to run it explicitly."
                ),
            }
        )
    )
    sys.exit(0)


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        allow()
        return

    # Cursor shape OR Claude shape
    cmd = (
        data.get("command")
        or (data.get("tool_input") or {}).get("command")
        or ""
    )
    if not isinstance(cmd, str) or not cmd.strip():
        allow()
        return

    # Soft-ask for amend/rebase/reset --hard before hard guard
    for pat in ASK_PATTERNS:
        if pat.search(cmd):
            ask(
                "history-affecting git command (rebase/amend/reset --hard) — "
                "approve only with explicit user intent"
            )
            return

    if not GUARD.is_file():
        allow("Score guard missing; fail-open")
        return

    # Project dir for secret-scan / rm-outside-workspace checks
    cwd = data.get("cwd") or data.get("working_directory") or os.getcwd()
    env = os.environ.copy()
    env.setdefault("CLAUDE_PROJECT_DIR", cwd)

    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    try:
        proc = subprocess.run(
            [sys.executable, str(GUARD)],
            input=payload,
            text=True,
            capture_output=True,
            timeout=12,
            env=env,
            cwd=cwd,
        )
    except Exception:
        allow("Score guard errored; fail-open")
        return

    if proc.returncode == 2:
        reason = (proc.stderr or "destructive command").strip().splitlines()
        reason = reason[0] if reason else "destructive command"
        # Strip the shared prefix if present
        reason = re.sub(r"^BLOCKED by Score risk-guard:\s*", "", reason)
        deny(reason)
        return

    allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        allow()
