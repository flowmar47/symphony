# Symphony

[![CI](https://github.com/flowmar47/symphony/actions/workflows/test.yml/badge.svg)](https://github.com/flowmar47/symphony/actions/workflows/test.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Multi-model orchestration for one conductor: **the invoking model conducts, frames specs,
reviews, and integrates; other seats execute.** Seats are filled at every invocation from
live discovery against what the host can run today, mapped to **Fast / Standard /
Frontier** bands, confirmed with the user, and every non-frontier return gets a separate
current-frontier review before acceptance or landing.

Engines supported on one bench: the host's native delegation tool (such as Claude Code's
Agent tool with the installed `symphony-*` seat definitions), plus four CLI engines
driven through one dispatcher — Codex (`codex`), Antigravity (`agy`), Cursor (`agent`),
and Claude Code (`claude -p`). Model IDs and efforts are discovered live; nothing here
ranks models, invents IDs, or pins a release.

## Install

```sh
git clone https://github.com/flowmar47/symphony
cd symphony
./install.sh
```

Installation requires a clean committed checkout. It builds a content-checked package
under `~/.symphony/packages/<commit>/symphony`, links it into Codex (`$CODEX_HOME`,
default `~/.codex`) and Claude (`$CLAUDE_CONFIG_DIR`, default `~/.claude`) skills, and
links the four seat definitions into `$CLAUDE_CONFIG_DIR/agents` (`--no-agents` skips
that). Use `--check` to verify installed symlinks and file digests, or `--uninstall` to
remove only Symphony-managed links cleanly. Existing managed links are updated; unexpected
files or links are refused; replaced links are backed up under `~/.symphony/backups`.
Nothing enables hooks, changes global model settings, or alters authentication.

Invoke **Symphony** in a new host session after installing or updating; a running session
does not reload its skill catalog or agent definitions.

## What an invocation does

1. Intake the request/handoff and re-verify premises against the current workspace.
2. Stay solo if the task is one bounded edit, discovery fails, or review overhead outweighs delegation.
3. Discover live capabilities: `python3 -B scripts/symphony-models.py --table`,
   `scripts/symphony-seat-plan.sh check`, plus any native subagent/model list.
4. **Confirm seats with the user** — **A**: reuse last confirmed seat plan (when available),
   **B**: proposal from live discovery mapped to Fast / Standard / Frontier bands,
   **C**: custom assignment — and save via `scripts/symphony-seat-plan.sh save`.
5. Decompose into lanes with disjoint writable scopes and written acceptance criteria.
6. Dispatch natively (`agents/symphony-*.md`) or via `scripts/symphony-dispatch.sh`.
7. Frontier-review every Fast/Standard/unknown-capability return (`symphony-accept.sh`).
8. Integrate, verify the whole, report problem-first, and land only with authorization.

See [the skill](skills/symphony/SKILL.md), [live routing](skills/symphony/references/routing.md),
[seat plans](skills/symphony/references/seat-plans.md), and the [CLI reference](skills/symphony/references/cli.md).

## CLI quick reference

```sh
python3 -B scripts/symphony-models.py --table
scripts/symphony-dispatch.sh builder high /abs/spec.md /abs/repo lane --engine <engine> --model <model> --effort <effort>
scripts/symphony-dispatch.sh builder auto /abs/spec.md /abs/repo lane --seat builder-light
scripts/symphony-dispatch.sh scout ask @/abs/brief.md /abs/repo facts --seat scout
scripts/symphony-dispatch.sh resume /abs/attempt/result.json /abs/fix-list.md
scripts/symphony-status.sh --table
scripts/symphony-accept.sh <attempt-or-run-id> --acceptance accepted --review completed --note "diff & tests checked"
```

Requires Python 3.9+ and an authenticated CLI for each engine you route to. Every run
records requested, resolved, and reported model/effort separately; `completed` is an
execution state, not acceptance.

## Discipline and verification

Scope delegates narrowly, avoid overlapping writes, and load only the relevant
[Score](score/OPERATING.md) drills. Inspect source-bound evidence; repeat checks when
source, inputs, or environment change, not by ritual. Only the conductor lands commits,
pushes, or releases. Run the unit suite after edits:

```sh
python3 -m unittest discover -s tests -v
```

**Validation status.** On 2026-09-20 each CLI engine completed a read-only lane through the
dispatcher and Cursor completed one write lane against a scratch repository ([CLI
reference](skills/symphony/references/cli.md)); ongoing routing quality is evaluated on
real work per [real-work assessment](skills/symphony/references/real-work-assessment.md).

MIT. Optional Score hooks remain host-specific and opt-in.
