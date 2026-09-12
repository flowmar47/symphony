# CLI fallback

Prefer native delegation when the host provides suitable controls. These commands
launch real agents except the catalog reader, status reader and `--dry-run`. Never use
them where agents are forbidden. Python 3.9+ and an authenticated compatible Codex CLI
are required; Symphony changes neither authentication nor global host configuration.

## Discovery and explicit routing

From the repository or installed package root:

```sh
python3 -B scripts/symphony-models.py
scripts/symphony-dispatch.sh builder high /absolute/spec.md /absolute/repo lane --model MODEL_ID
scripts/symphony-dispatch.sh scout ask @/absolute/brief.md /absolute/repo facts --model MODEL_ID --effort auto
scripts/symphony-dispatch.sh scout plan @/absolute/research.md /absolute/repo research --model MODEL_ID --effort high
```

Replace `MODEL_ID` with an exact ID returned by current discovery. The catalog reader
starts a short-lived `codex app-server` process and uses only `initialize`, `initialized`
and paginated `model/list`. It does not start a thread or inference turn. It has a
30-second/100-page budget and refuses incomplete results. It never reads private model
caches. Interface/authorization errors stop discovery without guessing a fallback;
discovery diagnostics are forwarded to stderr.

Model precedence: `--model`, then `SYMPHONY_BUILDER_MODEL`/`SYMPHONY_SCOUT_MODEL`, then
`SYMPHONY_MODEL`, then the catalog's sole recommended default. Effort precedence:
`--effort`, then the builder's positional effort or `SYMPHONY_SCOUT_EFFORT` (default
`auto`). `auto` resolves to the selected model's advertised default. Explicit unsupported
model/effort selections fail. Every run still passes its resolved model and effort
explicitly to Codex. The script does not assign qualitative economy/frontier rankings;
the conductor makes and records those decisions from current evidence.

An auto-selected delegating effort is refused. An explicitly selected delegating effort
requires `--allow-nested-delegation`, which attests that the conductor checked actual
authorization and compatible host concurrency limits. The flag cannot grant permission
or enforce host-wide concurrency. A wall-clock budget defaults to 480 seconds and can be
set with `--max-seconds`. Symphony never adds a premium service-tier override; separately
configured host choices remain the user's responsibility. Catalog descriptions are
useful signals, not a security boundary for undocumented execution modes.

## Non-launching dry run

Add `--dry-run` to print the resolved arguments, working directory, sandbox, model,
effort and pending acceptance state. It reads live model metadata but launches **no
lane**, creates no run record and performs no task. The displayed output path is an
explicit placeholder for a future private attempt directory, not an existing artifact.
No fake process or synthetic catalog is used.

## Reports, failure and one repair

Runs create separate owner-only attempt directories below `~/.symphony/runs` (override
with `SYMPHONY_OUT`). Lane names allow ASCII letters, digits, underscores and hyphens;
they never become paths. Each directory retains the brief, catalog snapshot, request,
PID/arguments, events, stderr, structured report and final result. Treat these as private
task data. No recursive cleanup or global cache deletion happens automatically.

The ledger defaults to `~/.symphony/runs/ledger.jsonl` (`SYMPHONY_LEDGER` overrides it).
Writes are locked. Existing output directories and ledger files must be owner-only;
the script refuses unsafe ones rather than silently changing their permissions. Use
canonical paths without symlinks for these directories. An older
`~/.symphony/ledger.jsonl` is left untouched; point the status reader's
`SYMPHONY_LEDGER` there when you need historical records.

Final states:

- `completed`: zero process exit, successful terminal event, valid completed report
  and no checks reported NOT RUN. **Still not conductor acceptance.**
- `partial`: clean execution with a partial report or checks explicitly NOT RUN.
- `failed`: nonzero exit, failure/error event, missing/malformed terminal/report,
  interruption, timeout or declared failure. A nonempty stale report cannot rescue it.

Exit codes are 0 for completed execution, 3 for partial, 1 for failed execution and 2
for pre-dispatch errors. Terminal errors are conservative even if the model later emits
output. Unknown event types are tolerated; absent usage/model telemetry stays null.
Requested/resolved identity is not proof of the provider's actual model. Host APIs can
report more detailed rerouting/usage than CLI events; use that evidence where available.

```sh
scripts/symphony-dispatch.sh resume /absolute/attempt/result.json /absolute/fix-list.md
scripts/symphony-status.sh 12
```

Resume accepts one original result with a thread ID, preserves its canonical working
directory, role, sandbox and research mode, and defaults to the original resolved
model/effort, ignoring new environment defaults on resume. Explicit flag overrides
still undergo fresh discovery. Its original request must agree with the result's
scope and route. An exclusive marker
prevents two repairs of one attempt. After a failed repair, the conductor takes over or
re-scopes; no automatic retry chain runs. The original scoped spec remains in the
resumed context. Never supply a different writable scope through a fix list.

Only the process group started by an invocation is signalled on timeout/cancellation.
Do not assume shell sandboxing restricts all external connectors: configured tools and
host policies still define their authority. Scoping and no-publication instructions
are not a replacement for those controls.

`symphony-status.sh` shows route, execution outcome, requested/resolved/reported
model/effort when available, usage, lane/routing durations, attempt and pending review/acceptance. It does not
print prompts or model answers. Historical ledger rows remain readable with missing
new fields shown as null.

The dispatcher never self-certifies frontier review. The conductor records the actual
review and acceptance in task records, citing the attempt. All lower-model returns
require frontier review, even if the CLI says `completed`.

## Interface sources and validation status

Inspected against Codex CLI 0.154.0 help and official documentation on 2026-09-12:
[app server/model discovery](https://learn.chatgpt.com/docs/app-server) and
[non-interactive JSON output](https://learn.chatgpt.com/docs/non-interactive-mode).
Actual model discovery, dispatch, resume, cancellation and routing effectiveness remain
**behaviorally unvalidated** in this release. No mocks, synthetic tests, simulated
agents or benchmarks were run. Test later on real work; it is not an installation gate.
