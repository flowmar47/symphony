# CLI engines and dispatch

Prefer native delegation when the host provides suitable controls. The commands here
launch real agents except the catalog reader, the seat-plan tool, the status reader and
`--dry-run`. Never use them where agents are forbidden. Python 3.9+ is required, plus an
authenticated CLI for each engine you route to; Symphony changes neither authentication
nor any host's global configuration.

## Discovery

From the repository or installed package root:

```sh
python3 -B scripts/symphony-models.py --table      # every engine, one line per model
python3 -B scripts/symphony-models.py --engine cursor --engine agy
scripts/symphony-seat-plan.sh check                # last confirmed plan against live catalogs
```

| Engine | Source of truth | What a row means |
|---|---|---|
| `codex` | `codex app-server` → `initialize`, `initialized`, paginated `model/list` (30 s / 100 pages, no thread, no inference) | model ID, listed efforts, default effort, whether it is the catalog default |
| `agy` | `agy models` | listed IDs folded by base model; the effort suffix (`-low`, `-high`) is the effort |
| `cursor` | `agent --list-models` | listed IDs folded by base model; effort suffix plus an optional `-fast` variant |
| `claude` | documented aliases (`opus`, `sonnet`, `haiku`) and efforts parsed from live `claude --help`; a full `claude-*` ID is accepted with `route_evidence: unverified-id` and the seat plan reports it `unverified` | the served model is only known from the run's `modelUsage`, which the record keeps as `reported_model` |

A composed ID (`<base>-<effort>-fast`) is only accepted when the host listed exactly
that ID. Discovery failures are reported per engine; nothing invents a catalog, reads
private caches or guesses successor IDs.

## Dispatch

```sh
scripts/symphony-dispatch.sh builder EFFORT /abs/spec.md /abs/repo LANE --engine ENGINE --model MODEL [--fast|--no-fast]
scripts/symphony-dispatch.sh builder auto /abs/spec.md /abs/repo LANE --seat SEAT
scripts/symphony-dispatch.sh scout ask  @/abs/brief.md /abs/repo LANE --engine ENGINE --model MODEL --effort EFFORT
scripts/symphony-dispatch.sh scout plan @/abs/research.md /abs/repo LANE --seat SEAT
```

Preference precedence: explicit flags (`--engine`, `--model`, `--effort`, `--fast` /
`--no-fast`), then `--seat <name>` from the confirmed seat plan (`~/.symphony/seat-plan.json`),
then `SYMPHONY_BUILDER_*` / `SYMPHONY_SCOUT_*`, then `SYMPHONY_*`, then Codex defaults
(other engines require an explicit model). For `auto` effort, Codex uses the model's
advertised default and `agy`/`cursor` use the bare un-suffixed model ID when listed.
Every run passes its resolved model and effort explicitly.

Per engine the lane becomes:

| Engine | Builder | Scout ask | Scout plan | Prompt | Report |
|---|---|---|---|---|---|
| codex | `exec` with `sandbox_mode=workspace-write`, `approval_policy=never` | `read-only` sandbox, `--skip-git-repo-check` | same as ask; the brief permits web | stdin | `--output-schema` → `report.json` |
| agy | `--mode accept-edits --add-dir DIR` | `--mode plan --add-dir DIR` | same | `--print` argument, prefixed with the working directory | last fenced JSON block of `response` |
| cursor | `-p --force --trust --workspace DIR` | `--mode ask` | `--mode plan` | positional argument | last fenced JSON block of the `result` event |
| claude | `-p --permission-mode acceptEdits --allowedTools Bash --disallowedTools Agent` | `--permission-mode plan`, no Agent/WebFetch/WebSearch | `--permission-mode plan`, no Agent | positional argument, first | `--json-schema` structured result, else fenced JSON |

The agy and cursor prompts carry the brief as an argument, so those briefs stay under
200 KiB; point at a file for anything larger. `--extra-arg=--flag` (repeatable) appends
one verbatim engine flag before the prompt. Flags that would change the lane's scope or
approval policy behind the record's back (`-c`, `--sandbox`, `--permission-mode`,
`--allowedTools`, `--mode`, `--force`, `--add-dir`, `--workspace`, anything
`--dangerously-*`) are refused; the one exception is `--dangerously-skip-permissions` on a
**builder** lane, for agy builders that must run commands unattended. The record keeps
`extra_args` and a `scope_control` field naming what actually bounds the lane: only Codex
runs in a sandbox; agy, Cursor and Claude lanes are bounded by engine mode or host
permission flags, which is policy, not isolation.

An auto-selected delegating effort is refused. An explicitly selected delegating effort
requires `--allow-nested-delegation`, which attests that the conductor checked
authorization and host concurrency limits; the flag grants nothing by itself. Only Codex
exposes the signal for this check (`ultra`, or an effort whose description mentions
delegation); agy and Cursor publish no such signal, and the Claude engine disallows the
Agent tool outright. `--max-seconds` (default 480) bounds the wall clock. Symphony never
adds a premium service-tier override.

### agy plan mode cannot run commands headless

An agy scout that needs a shell command gets it auto-denied (`denied_actions` in the
record, empty response, state `failed`), because headless plan mode cannot prompt. agy
scouts read files only; route command-requiring research to a Codex or Claude scout, or
add an allow-rule in agy's own settings outside Symphony.

### Cursor's exit lag

The Cursor CLI's own `duration_ms` is the answer time; the process then idles about
50 seconds before it exits, and its buffered `stream-json` output only reaches the file
one second before that exit, so nothing upstream can cut the wait short. Budget every
Cursor lane as answer time plus a minute, and add it to the lane's cost. Measured on
2026-09-20 over five runs (43–81 s of API time, 93–131 s of wall time); one further
trivial probe printed nothing for 150 s, so keep `--max-seconds` realistic.

### Nested Claude Code

`claude -p` refuses to run inside another Claude Code session unless the nested-session
variables are cleared; the dispatcher launches it with `CLAUDECODE`,
`CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_EFFORT` and the session identifiers removed. Requested
`haiku` was served as `claude-sonnet-5` on this bench; always read `reported_model`.

## Non-launching dry run

Add `--dry-run` to print the resolved engine, model, effort, fast variant, sandbox, argv
and prompt channel. It reads live catalogs but launches **no lane**, creates no run
record and performs no task.

## Records, failure and one repair

Runs create separate owner-only attempt directories below `~/.symphony/runs` (override
with `SYMPHONY_OUT`). Each holds the spec as given (`spec.txt`), the prompt as sent
(`brief.txt`), catalog snapshot, request, argv, raw engine output (`events.jsonl`),
stderr, the structured report and the final result.
Treat these as private task data. The ledger defaults to `~/.symphony/runs/ledger.jsonl`
(`SYMPHONY_LEDGER` overrides). Writes are locked; unsafe permissions are refused rather
than fixed; paths must be canonical.

Final states:

- `completed`: zero exit, a successful terminal event, a valid report and nothing NOT
  RUN. **Still not conductor acceptance.**
- `partial`: clean execution with a partial report or checks explicitly NOT RUN.
- `failed`: nonzero exit, failure event, empty response, missing or malformed report,
  interruption, timeout or a declared failure. A stale report cannot rescue it.

Exit codes: 0 completed, 3 partial, 1 failed, 2 pre-dispatch error. Absent telemetry
stays null. Requested and resolved identity are not proof of the served model.

```sh
scripts/symphony-dispatch.sh resume /abs/attempt/result.json /abs/fix-list.md [--no-fast]
scripts/symphony-status.sh 12 --table
scripts/symphony-status.sh --failed --lane <name>
scripts/symphony-status.sh --summary
scripts/symphony-accept.sh <attempt-or-run-id> --acceptance accepted --review completed --note "evidence checked"
```

Resume is the one permitted repair. It stays on the original engine, directory, role,
sandbox and mode, and defaults to the original model, effort and fast variant. Codex
resumes the recorded thread with the fix list as the new turn; agy, cursor and claude
start a fresh lane whose brief is the original `spec.txt` plus the fix list. An exclusive
marker (`repair-claimed.json`) prevents two repairs of one attempt before creating a new
run directory. After a failed repair the conductor re-scopes or moves the lane to a
stronger seat; no automatic retry chain runs. Never widen the writable scope through a
fix list.

Only the process group started by an invocation is signalled on timeout or cancellation
(SIGTERM/SIGINT returns exit 130). Shell sandboxing does not restrict configured
connectors; host policies define their authority.

`symphony-status.sh` shows engine, route, execution outcome, requested/resolved/reported
model and effort, usage, durations, attempt and pending review/acceptance (`--table`,
`--summary`, `--lane`, `--failed`). `symphony-accept.sh` updates `result.json` atomically
and appends the acceptance/review verdict to `ledger.jsonl`. Neither prints prompts or
model answers. Install verification (`./install.sh --check`) and removal (`./install.sh
--uninstall`) respect `CODEX_HOME` and `CLAUDE_CONFIG_DIR`.

## Seat plans

```sh
scripts/symphony-seat-plan.sh show
scripts/symphony-seat-plan.sh save plan.json     # or: save -  (JSON on stdin)
```

A plan is `{"seats": {"<seat>": {"engine", "model", "effort", "fast"?, "note"?}}}` and is
stored at `~/.symphony/seat-plan.json` (`SYMPHONY_SEAT_PLAN` overrides). `save` refuses a
plan with any non-native seat that does not resolve against live discovery; a full
`claude-*` ID is stored but reported `unverified`. Engine `native` marks a host delegation
seat the script cannot verify; the conductor confirms it in-session. The stored plan is the **A** option of the next invocation's availability
question, never an automatic route.

## Validation status

Interfaces were inspected against Codex CLI 0.155.1, agy 1.2.7, Cursor agent
2026.09.18 and Claude Code 2.1.278 on 2026-09-20. Each engine completed one read-only
lane through the dispatcher on that date, and Cursor completed one write lane; the
resulting records are the evidence, not a benchmark. Routing effectiveness, repair and
cancellation on real work remain to be assessed as work arises.
