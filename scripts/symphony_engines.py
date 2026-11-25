"""Engine adapters: discover each CLI host's catalog and build one lane command.

An engine is a CLI that can run one bounded, non-interactive lane: Codex, Antigravity
(`agy`), Cursor (`agent`) or Claude Code (`claude`). Native host delegation (the Agent
tool) is not an engine here; the conductor drives it directly. Every adapter exposes the
same surface so the dispatcher, ledger and status reader stay engine-agnostic:

    discover(cwd)                 -> catalog rows {model, efforts, default_effort, ids, fast}
    resolve(rows, model, effort, fast) -> (cli_model_id, effort, nested)
    command(job, attempt, brief, schema) -> argv, stdin mode
    inspect(attempt)              -> terminal/usage/reported identity/response text
    report_from(inspection, attempt) -> parsed report dict or None

Model and effort values are runtime data read from the host; nothing here ranks models.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import shutil
import subprocess

from symphony_catalog import discover as codex_discover, is_nested_effort

DISCOVERY_SECONDS = 45
SUFFIX_EFFORTS = ("extra-high", "minimal", "medium", "xhigh", "none", "high", "max", "low")
STANDALONE_MODEL_SUFFIXES = ("max", "medium", "none")
ARGV_BRIEF_LIMIT = 200 * 1024
CLAUDE_ALIASES = ("opus", "sonnet", "haiku")
CLAUDE_EFFORTS = ("low", "medium", "high", "xhigh", "max")
CLAUDE_FULL_ID = re.compile(r"claude-[a-z0-9][a-z0-9.-]*")
# Flags that would change a lane's scope, identity, output framing, or approval policy behind the record's back.
SHORT_BLOCKED_PREFIXES = ("-c", "-s", "-m", "-p", "-a", "-C")
SCOPE_FLAGS = (
    "-c", "-s", "-m", "-p", "-a", "-C",
    "--sandbox", "--permission-mode", "--permission-prompts",
    "--allowedTools", "--allowed-tools", "--disallowedTools", "--disallowed-tools",
    "--mode", "--force", "--yolo", "--approve-for-me",
    "--dangerously-bypass-approvals-and-sandbox", "--dangerously-bypass-hook-trust",
    "--dangerously-skip-permissions",
    "--add-dir", "--workspace", "--worktree", "--cd",
    "--auto-review", "--approve-mcps",
    "--model", "--effort", "--config", "--full-auto",
    "--ask-for-approval", "--tools", "--settings", "--mcp-config",
    "--output-format", "--print", "--json-schema",
)
BUILDER_ONLY_FLAGS = ("--dangerously-skip-permissions",)
NESTED_ENV = (
    "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_EFFORT", "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_MESSAGING_SOCKET",
    "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_BRIDGE_SESSION_ID", "CLAUDE_PID",
)
REPORT_CONTRACT = (
    "\n\nFINAL REPORT CONTRACT: end your final message with exactly one fenced ```json block "
    "and nothing after it, shaped {\"status\": \"completed\"|\"partial\"|\"failed\", \"summary\": str, "
    "\"files\": [str], \"evidence\": [str], \"not_run\": [str]}. Evidence entries name the command, "
    "exit code and output path. not_run lists only checks the brief required that you did not execute "
    "(empty when none); do not list actions the brief forbade."
)


class EngineError(ValueError):
    pass


def check_extra_args(seat, extra_args, engine=None):
    """Extra flags may tune an engine, never widen scope, identity, or approval policy."""
    for extra in extra_args:
        if not extra.startswith("-") or any(char in extra for char in "\0\n"):
            raise EngineError("Each --extra-arg must be one engine flag")
        head = extra.split("=", 1)[0]
        if head in BUILDER_ONLY_FLAGS and seat == "builder" and engine in (None, "agy"):
            continue
        compact_short = (
            not head.startswith("--")
            and len(head) > 2
            and any(head.startswith(short) for short in SHORT_BLOCKED_PREFIXES)
        )
        if head in SCOPE_FLAGS or head.startswith("--dangerously") or compact_short:
            raise EngineError(
                f"{head} changes the lane's scope, identity, or approval policy; the seat or dispatcher flags decide that"
            )


def capture(argv, cwd=None, timeout=DISCOVERY_SECONDS, env=None):
    try:
        done = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True,
                              timeout=timeout, check=False, env=env)
    except subprocess.TimeoutExpired as error:
        raise EngineError(f"{argv[0]} discovery exceeded {timeout} seconds") from error
    if done.returncode != 0:
        detail = done.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise EngineError(f"{argv[0]} discovery exited {done.returncode}: {detail[-1] if detail else 'no stderr'}")
    return done.stdout.decode("utf-8", errors="replace")


def split_variant(identifier):
    """'cursor-grok-4.6-xhigh-fast' -> ('cursor-grok-4.6', 'xhigh', True); 'gpt-5.2' -> ('gpt-5.2', None, False)."""
    fast = identifier.endswith("-fast")
    base = identifier[:-5] if fast else identifier
    for effort in SUFFIX_EFFORTS:
        if base.endswith("-" + effort):
            return base[:-len(effort) - 1], effort, fast
    return base, None, fast


def group_variants(identifiers):
    """Fold listed IDs into rows keyed by base model; every composed ID is one the host listed."""
    parsed = [(identifier, *split_variant(identifier)) for identifier in identifiers]
    base_counts = {}
    for _, base, _, _ in parsed:
        base_counts[base] = base_counts.get(base, 0) + 1
    rows = {}
    for identifier, base, effort, fast in parsed:
        # Preserve standalone model IDs (e.g. qwen-max, mistral-medium) when no base model or sibling exists.
        if effort in STANDALONE_MODEL_SUFFIXES and not fast and base_counts.get(base, 0) == 1:
            base, effort = identifier, None
        row = rows.setdefault(base, {"model": base, "efforts": [], "default_effort": None, "fast": False, "ids": {}})
        key = effort or "default"
        if key not in row["efforts"]:
            row["efforts"].append(key)
        if key == "default" and row["default_effort"] is None:
            row["default_effort"] = "default"
        row["fast"] = row["fast"] or fast
        row["ids"][f"{key}|{'fast' if fast else 'normal'}"] = identifier
    return list(rows.values())


def resolve_variant(rows, requested_model, requested_effort, fast):
    if requested_model is None:
        raise EngineError("This engine has no default model; pass --model from live discovery")
    matches = [row for row in rows if row["model"] == requested_model]
    if len(matches) != 1:
        raise EngineError(f"Model {requested_model!r} is not in this engine's live catalog")
    row = matches[0]
    effort = requested_effort
    if effort in (None, "auto"):
        effort = "default" if "default" in row["efforts"] else None
    if effort is None:
        raise EngineError(f"Model {requested_model!r} needs an explicit effort from {row['efforts']}")
    key = f"{effort}|{'fast' if fast else 'normal'}"
    if key not in row["ids"]:
        raise EngineError(f"Model {requested_model!r} does not list effort {effort!r}"
                          f"{' with the fast variant' if fast else ''}; listed: {sorted(row['ids'])}")
    return row["ids"][key], effort, False


def _extract_balanced_json_dicts(text):
    candidates = []
    index = 0
    length = len(text)
    while index < length:
        if text[index] != "{":
            index += 1
            continue
        depth = 0
        in_string = False
        escaped = False
        pos = index
        while pos < length:
            ch = text[pos]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidates.append(text[index:pos + 1])
                        break
            pos += 1
        index += 1
    return candidates


def extract_report(text):
    """The last fenced JSON object in a final message, or a balanced inline JSON object."""
    if not isinstance(text, str) or not text.strip():
        return None
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S | re.I)
    for block in reversed(blocks):
        try:
            value = json.loads(block)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    try:
        value = json.loads(text.strip())
        if isinstance(value, dict):
            return value
    except ValueError:
        pass
    for snippet in reversed(_extract_balanced_json_dicts(text)):
        try:
            value = json.loads(snippet)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def read_json_lines(path):
    with open(path, "rb") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except ValueError:
                yield None
                continue
            yield value if isinstance(value, dict) else None


class Codex:
    name = "codex"
    binary = "codex"
    prompt_via = "stdin"
    scope_control = {"builder": "sandbox_mode=workspace-write", "scout": "sandbox_mode=read-only"}

    def discover(self, cwd):
        binary = shutil.which(self.binary)
        if binary is None:
            raise EngineError("codex is not on PATH")
        rows = []
        for model in codex_discover(binary, cwd):
            efforts = [option["reasoningEffort"] for option in model.get("supportedReasoningEfforts") or []
                       if isinstance(option, dict) and isinstance(option.get("reasoningEffort"), str)]
            rows.append({"model": model["model"], "efforts": efforts,
                         "default_effort": model.get("defaultReasoningEffort"), "fast": False,
                         "is_default": model.get("isDefault") is True, "raw": model})
        return rows

    def resolve(self, rows, requested_model, requested_effort, fast):
        if fast:
            raise EngineError("codex has no fast variant")
        if requested_model is None:
            matches = [row for row in rows if row.get("is_default")]
        else:
            matches = [row for row in rows if row["model"] == requested_model]
        if len(matches) != 1:
            raise EngineError("Requested model unavailable, or no unique default; select an ID from live discovery")
        row = matches[0]
        if not row["efforts"]:
            raise EngineError("Model does not expose supported efforts; choose one explicitly on a compatible host")
        effort = row["default_effort"] if requested_effort in (None, "auto") else requested_effort
        if effort not in row["efforts"]:
            raise EngineError(f"Effort {effort!r} is not supported by {row['model']}; listed: {row['efforts']}")
        options = {option["reasoningEffort"]: option for option in row["raw"].get("supportedReasoningEfforts", [])}
        nested = is_nested_effort(row["raw"], effort, options.get(effort, {}))
        if requested_effort in (None, "auto") and nested:
            raise EngineError("Default effort may delegate; choose an explicit non-delegating effort")
        return row["model"], effort, nested

    def command(self, job, attempt, brief, schema):
        command = [shutil.which(self.binary), "exec"]
        if job.get("thread"):
            command.append("resume")
        command += ["--model", job["resolved_model"],
                    "-c", "model_reasoning_effort=" + json.dumps(job["resolved_effort"]),
                    "-c", "sandbox_mode=" + json.dumps(job["sandbox"]),
                    "-c", 'approval_policy="never"',
                    "--json", "--output-schema", str(schema), "-o", str(attempt / "report.json")]
        if job["seat"] == "scout":
            command.append("--skip-git-repo-check")
        command += job.get("extra_args", [])
        if job.get("thread"):
            command.append(job["thread"])
        command.append("-")
        return command

    def environment(self):
        return None

    def inspect(self, attempt):
        result = {"thread": None, "terminal": None, "usage": None, "reported_model": None,
                  "reported_effort": None, "event_error": False, "response": None}
        for event in read_json_lines(attempt / "events.jsonl"):
            if event is None or not isinstance(event.get("type"), str):
                result["event_error"] = True
                continue
            kind = event["type"]
            if kind == "thread.started":
                result["thread"] = event.get("thread_id")
            if kind == "turn.started":
                result["terminal"] = None
            if kind in ("turn.completed", "turn.failed"):
                result["terminal"] = "completed" if kind == "turn.completed" else "failed"
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

    def report_from(self, inspection, attempt):
        return None  # codex writes report.json itself through --output-schema


class Agy:
    name = "agy"
    binary = "agy"
    prompt_via = "argv"
    scope_control = {"builder": "--mode accept-edits (engine policy, not a sandbox)", "scout": "--mode plan (engine policy, not a sandbox)"}

    def discover(self, cwd):
        binary = shutil.which(self.binary)
        if binary is None:
            raise EngineError("agy is not on PATH")
        identifiers = []
        for line in capture([binary, "models"], cwd=cwd).splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", parts[0]):
                identifiers.append(parts[0])
        if not identifiers:
            raise EngineError("agy models listed nothing parseable")
        return group_variants(identifiers)

    def resolve(self, rows, requested_model, requested_effort, fast):
        if fast:
            raise EngineError("agy has no fast variant")
        return resolve_variant(rows, requested_model, requested_effort, False)

    def command(self, job, attempt, brief, schema):
        # Plan mode otherwise runs in agy's own scratch workspace; the lane directory must be added explicitly.
        mode = "accept-edits" if job["seat"] == "builder" else "plan"
        return [shutil.which(self.binary), "--model", job["resolved_model"], "--output-format", "json",
                "--print-timeout", f"{job['max_seconds']}s", "--mode", mode, "--add-dir", job["directory"],
                *job.get("extra_args", []), "--print", f"WORKING DIRECTORY: {job['directory']}\n\n" + brief + REPORT_CONTRACT]

    def environment(self):
        return None

    def inspect(self, attempt):
        result = {"thread": None, "terminal": None, "usage": None, "reported_model": None,
                  "reported_effort": None, "event_error": False, "response": None}
        try:
            payload = json.loads((attempt / "events.jsonl").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            result["event_error"] = True
            return result
        if not isinstance(payload, dict):
            result["event_error"] = True
            return result
        result["thread"] = payload.get("conversation_id")
        result["usage"] = payload.get("usage") if isinstance(payload.get("usage"), dict) else None
        if isinstance(payload.get("denied_actions"), list) and payload["denied_actions"]:
            # Headless agy auto-denies tools that need a permission prompt; the lane then returns nothing.
            result["denied_actions"] = payload["denied_actions"]
        response = payload.get("response")
        result["response"] = response if isinstance(response, str) else None
        num_turns = payload.get("num_turns")
        has_turns = isinstance(num_turns, int) and not isinstance(num_turns, bool) and num_turns >= 1
        if payload.get("status") == "SUCCESS" and result["response"] and has_turns:
            result["terminal"] = "completed"
        else:
            result["terminal"] = "failed"
            result["event_error"] = True
        return result

    def report_from(self, inspection, attempt):
        return extract_report(inspection.get("response"))


class Cursor:
    name = "cursor"
    binary = "agent"
    prompt_via = "argv"
    scope_control = {"builder": "--force (engine policy, not a sandbox)", "scout": "--mode ask|plan (engine policy, not a sandbox)"}

    def discover(self, cwd):
        binary = shutil.which(self.binary)
        if binary is None:
            raise EngineError("agent (Cursor CLI) is not on PATH")
        identifiers = []
        for line in capture([binary, "--list-models"], cwd=cwd).splitlines():
            match = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*) - ", line)
            if match:
                identifiers.append(match.group(1))
        if not identifiers:
            raise EngineError("agent --list-models listed nothing parseable")
        return group_variants(identifiers)

    def resolve(self, rows, requested_model, requested_effort, fast):
        return resolve_variant(rows, requested_model, requested_effort, fast)

    def command(self, job, attempt, brief, schema):
        command = [shutil.which(self.binary), "-p", "--output-format", "stream-json", "--trust",
                   "--workspace", job["directory"], "--model", job["resolved_model"]]
        if job["seat"] == "builder":
            command.append("--force")
        else:
            command += ["--mode", job["mode"]]
        command += job.get("extra_args", [])
        command.append(brief + REPORT_CONTRACT)
        return command

    def environment(self):
        return None

    def inspect(self, attempt):
        result = {"thread": None, "terminal": None, "usage": None, "reported_model": None,
                  "reported_effort": None, "event_error": False, "response": None}
        for event in read_json_lines(attempt / "events.jsonl"):
            if event is None or not isinstance(event.get("type"), str):
                result["event_error"] = True
                continue
            if event["type"] == "system" and isinstance(event.get("model"), str):
                result["reported_model"] = event["model"]
            if isinstance(event.get("session_id"), str):
                result["thread"] = event["session_id"]
            if event["type"] == "result":
                result["usage"] = event.get("usage") if isinstance(event.get("usage"), dict) else None
                text = event.get("result")
                result["response"] = text if isinstance(text, str) else None
                ok = event.get("subtype") == "success" and event.get("is_error") is False and result["response"]
                result["terminal"] = "completed" if ok else "failed"
                if not ok:
                    result["event_error"] = True
        return result

    def report_from(self, inspection, attempt):
        return extract_report(inspection.get("response"))


def discover_claude_efforts(binary, cwd):
    """Parse supported --effort levels from `claude --help`, falling back cleanly if omitted."""
    try:
        help_text = capture([binary, "--help"], cwd=cwd)
    except (EngineError, OSError):
        return list(CLAUDE_EFFORTS)
    match = re.search(r"--effort\s+[^\n]*(?:\n[ \t]+[^\n]*)*?\(([a-z0-9,\s-]+)\)", help_text, re.I)
    if not match:
        return list(CLAUDE_EFFORTS)
    efforts = [token.strip() for token in match.group(1).split(",") if re.fullmatch(r"[a-z0-9][a-z0-9-]*", token.strip())]
    return efforts or list(CLAUDE_EFFORTS)


class Claude:
    name = "claude"
    binary = "claude"
    prompt_via = "argv"
    scope_control = {"builder": "--permission-mode acceptEdits + Bash (host permissions, not a sandbox)", "scout": "--permission-mode plan (host permissions, not a sandbox)"}

    def discover(self, cwd):
        binary = shutil.which(self.binary)
        if binary is None:
            raise EngineError("claude is not on PATH")
        version = capture([binary, "--version"], cwd=cwd).strip()
        efforts = discover_claude_efforts(binary, cwd)
        rows = [{"model": alias, "efforts": list(efforts), "default_effort": None, "fast": False,
                 "source": f"documented alias for {version}; the served model is reported after the run"}
                for alias in CLAUDE_ALIASES]
        return rows

    def resolve(self, rows, requested_model, requested_effort, fast):
        if fast:
            raise EngineError("claude CLI fast mode is not driven by Symphony; pass it through --extra-arg if the host allows it")
        if requested_model is None:
            raise EngineError("claude needs an explicit --model alias or full model ID")
        supported_efforts = list(rows[0]["efforts"]) if rows and isinstance(rows[0].get("efforts"), list) and rows[0]["efforts"] else list(CLAUDE_EFFORTS)
        if requested_effort in (None, "auto"):
            raise EngineError(f"claude needs an explicit --effort from {supported_efforts}")
        if requested_effort not in supported_efforts:
            raise EngineError(f"Effort {requested_effort!r} is not a documented claude effort {supported_efforts}")
        if requested_model not in CLAUDE_ALIASES and not CLAUDE_FULL_ID.fullmatch(requested_model):
            raise EngineError(f"claude takes a documented alias {list(CLAUDE_ALIASES)} or a full claude-* model ID")
        return requested_model, requested_effort, False

    def verified(self, requested_model):
        """Aliases are documented; a full ID is only proven by the served model after the run."""
        return requested_model in CLAUDE_ALIASES

    def command(self, job, attempt, brief, schema):
        # The prompt goes first: the tool-list options are variadic and would swallow a trailing positional.
        command = [shutil.which(self.binary), "-p", brief, "--model", job["resolved_model"], "--effort", job["resolved_effort"],
                   "--output-format", "json", "--json-schema", schema.read_text(encoding="utf-8"),
                   "--permission-prompts", "none"]
        if job["seat"] == "builder":
            command += ["--permission-mode", "acceptEdits", "--allowedTools", "Bash", "--disallowedTools", "Agent"]
        elif job["mode"] == "plan":
            command += ["--permission-mode", "plan", "--disallowedTools", "Agent"]
        else:
            command += ["--permission-mode", "plan", "--disallowedTools", "Agent,WebFetch,WebSearch"]
        command += job.get("extra_args", [])
        return command

    def environment(self):
        return {key: value for key, value in os.environ.items() if key not in NESTED_ENV}

    def inspect(self, attempt):
        result = {"thread": None, "terminal": None, "usage": None, "reported_model": None,
                  "reported_effort": None, "event_error": False, "response": None}
        try:
            events = json.loads((attempt / "events.jsonl").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            result["event_error"] = True
            return result
        if not isinstance(events, list):
            result["event_error"] = True
            return result
        for event in events:
            if not isinstance(event, dict):
                result["event_error"] = True
                continue
            if isinstance(event.get("session_id"), str):
                result["thread"] = event["session_id"]
            if event.get("type") != "result":
                continue
            if isinstance(event.get("permission_denials"), list) and event["permission_denials"]:
                result["denied_actions"] = event["permission_denials"]
            usage = event.get("modelUsage")
            if isinstance(usage, dict) and usage:
                result["reported_model"] = ",".join(sorted(usage))
                result["usage"] = {"models": usage, "total_cost_usd": event.get("total_cost_usd")}
            structured = event.get("structured_output")
            text = event.get("result")
            result["response"] = json.dumps(structured) if isinstance(structured, dict) else (text if isinstance(text, str) else None)
            ok = event.get("is_error") is False and event.get("subtype") == "success" and result["response"]
            result["terminal"] = "completed" if ok else "failed"
            if not ok:
                result["event_error"] = True
        return result

    def report_from(self, inspection, attempt):
        return extract_report(inspection.get("response"))


ENGINES = {engine.name: engine for engine in (Codex(), Agy(), Cursor(), Claude())}


def engine_named(name):
    if name not in ENGINES:
        raise EngineError(f"Unknown engine {name!r}; known: {sorted(ENGINES)}")
    return ENGINES[name]


def _discover_one(name, cwd):
    engine = engine_named(name)
    binary = shutil.which(engine.binary)
    try:
        rows = engine.discover(cwd)
        return {"ok": True, "binary": shutil.which(engine.binary) or binary, "models": rows}
    except (EngineError, ValueError, OSError) as error:
        return {"ok": False, "binary": binary, "error": str(error), "models": []}


def discover_all(cwd, names=None):
    """Per-engine catalogs run concurrently; one failure is recorded without blocking others."""
    targets = list(names or sorted(ENGINES))
    for name in targets:
        engine_named(name)
    if len(targets) <= 1:
        return {name: _discover_one(name, cwd) for name in targets}
    report = {}
    with ThreadPoolExecutor(max_workers=min(4, len(targets))) as pool:
        futures = {name: pool.submit(_discover_one, name, cwd) for name in targets}
        for name in targets:
            report[name] = futures[name].result()
    return report
