#!/usr/bin/env python3
# ENFORCES: Prime Directive 12 + Integrity I-6 (gate destructive cmds) and I-8 (no secret commits).
# MAPS TO: AUDIT.md rows Directive-12, I-6, I-8, git-discipline skill.
# TEST: echo '{"tool_name":"Bash","tool_input":{"command":"git push --force"}}' | python3 pre-tool-guard.py; echo "exit=$?"  (expect exit 2 + reason)
"""PreToolUse(Bash) guard for the Symphony Score.

Denies the destructive tier the base catastrophic-guard leaves open: force pushes, history
rewrites, DROP/TRUNCATE, mass chmod, curl|sh, recursive deletes outside the workspace — and
blocks commits that stage an obvious secret. Deny = exit 2 with a reason (verified: PreToolUse
exit 2 blocks the call and feeds stderr to Claude). Fail-safe: any internal error exits 0 so a
bug in this guard never bricks the session. The model can ask the user for explicit approval.
"""

import json
import os
import re
import subprocess
import sys


def deny(reason: str) -> None:
    sys.stderr.write(
        f"BLOCKED by Score risk-guard: {reason}\n"
        "This is destructive or irreversible. If you truly intend it, ask the user for "
        "explicit approval in chat and have them run it, or narrow the scope.\n"
    )
    sys.exit(2)


def main() -> None:
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        sys.exit(0)
    cmd = (data.get("tool_input", {}) or {}).get("command", "") or ""
    c = " ".join(cmd.split())  # normalize whitespace
    project = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # 1. Force push / history rewrite.
    if re.search(r"\bgit\s+push\b[^|;&]*(--force\b(?!-with-lease)|(?<!-)\s-f\b)", c):
        deny("git force push (rewrites remote history)")
    if re.search(r"\bgit\s+(rebase|filter-branch|filter-repo)\b", c):
        deny("git history rewrite (rebase/filter)")
    if re.search(r"\bgit\s+commit\b[^|;&]*--amend", c):
        deny("git commit --amend (rewrites an existing commit)")
    if re.search(r"\bgit\s+reset\s+--hard\b", c):
        deny("git reset --hard (discards uncommitted work)")
    if re.search(r"\bgit\s+push\b[^|;&]*:\S", c) or re.search(
        r"\bgit\s+push\b[^|;&]*--delete", c
    ):
        deny("git push deleting a remote branch")

    # 2. SQL data destruction — only when clearly executing SQL (not echo/printf text).
    sql_exec = re.search(
        r"\b(psql|mysql|mysqlsh|sqlite3|sqlcmd|cockroach|clickhouse-client|prisma|supabase)\b",
        c,
        re.I,
    ) or re.search(r"\b(-c|--command|--execute|-e)\b", c)
    if sql_exec and re.search(
        r"\b(drop\s+(table|database|schema)|truncate\s+table)\b", c, re.I
    ):
        deny("SQL DROP/TRUNCATE (destroys data/schema)")

    # 3. Mass chmod/chown on a broad or absolute-root target.
    if re.search(
        r"\bchmod\s+-[a-zA-Z]*R[a-zA-Z]*\s+\S+\s+(/|~|~/|\$HOME|\$\{HOME\}|\.|\*)(?:\s|$)",
        c,
    ):
        deny("recursive chmod on a root/home/cwd/glob target")
    if re.search(
        r"\bchown\s+-[a-zA-Z]*R[a-zA-Z]*\s+\S+\s+(/|~|~/|\$HOME|\$\{HOME\}|\.)(?:\s|$)",
        c,
    ):
        deny("recursive chown on a root/home/cwd target")

    # 4. curl|wget piped straight into a shell.
    if re.search(r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(sh|bash|zsh|python3?)\b", c):
        deny("piping a remote download straight into a shell (curl|sh)")

    # 5. Recursive force-delete of an absolute path outside the project workspace.
    for m in re.finditer(r"\brm\b([^|;&\n]*)", c):
        seg = m.group(1)
        rec = re.search(r"(?:^|\s)-[a-zA-Z]*r[a-zA-Z]*\b", seg) or "--recursive" in seg
        force = re.search(r"(?:^|\s)-[a-zA-Z]*f[a-zA-Z]*\b", seg) or "--force" in seg
        if not (rec and force):
            continue
        # catastrophic roots
        if re.search(
            r"(?:^|\s)['\"]?(/|/\*|~|~/|\$HOME|\$\{HOME\}|\.|\./)['\"]?(?=\s|$)", seg
        ):
            deny("recursive force-delete of a root / home / cwd target")
        # any absolute path not under the project dir
        for tok in re.findall(r"(?:^|\s)(/[^\s'\"]+)", seg):
            if not os.path.abspath(tok).startswith(os.path.abspath(project)):
                deny(f"recursive force-delete outside the workspace: {tok}")

    # 6. Secret about to be committed: scan the staged diff on a git commit.
    if re.search(r"\bgit\s+commit\b", c):
        try:
            diff = subprocess.run(
                ["git", "diff", "--cached", "--unified=0"],
                cwd=project,
                capture_output=True,
                text=True,
                timeout=8,
            ).stdout
        except Exception:
            diff = ""
        secret_pats = [
            (r"-----BEGIN[ A-Z]*PRIVATE KEY-----", "private key"),
            (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key id"),
            (r"\bsk-[A-Za-z0-9]{20,}\b", "API secret key (sk-…)"),
            (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "GitHub token"),
            (
                r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*['\"][^'\"]{6,}",
                "hardcoded credential",
            ),
        ]
        for line in diff.splitlines():
            if not line.startswith("+"):
                continue
            for pat, what in secret_pats:
                if re.search(pat, line):
                    deny(
                        f"staged diff contains a {what} — unstage it and use env vars / a secret manager (rotation needed if already pushed)"
                    )

    sys.exit(0)


try:
    main()
except SystemExit:
    raise
except Exception:
    sys.exit(0)  # fail-safe: never brick the session
