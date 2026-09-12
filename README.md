# Symphony

Model-agnostic orchestration: **one conductor, appropriately sized work, frontier
review of lower-model returns, evidence before acceptance**. Native delegation is
preferred; Codex CLI lanes remain available when the host permits them.

Select models and efforts from current host capabilities. Initial provisional candidates
are Luna for clear bounded work, Sol for substantial implementation, and Astra for hard
reasoning and frontier review. These are guidance, not hard-coded IDs or measured
rankings. Every lower-capability return receives a frontier-model review before
acceptance, at an effort appropriate to its complexity and risk.

## Install

```sh
git clone https://github.com/flowmar47/symphony
cd symphony
./install.sh
```

Installation requires a clean committed checkout. It builds a complete content-checked
package under `~/.symphony/packages/<commit>/symphony` and links it into Codex and Claude
skills. Existing managed links can be updated; unexpected files or links are refused.
Replaced links are retained under `~/.symphony/backups`. Nothing enables hooks, changes
global model configuration or alters authentication. `--codex` and `--claude` select
one host; no arguments selects both. Codex respects `CODEX_HOME` when set.

Invoke **Symphony** in a new host session. Installation does not force an already-
running session to reload its skill catalog.

## CLI fallback

Requires Python 3.9+ and an authenticated Codex CLI with `app-server` `model/list`,
`exec --json`, model/effort overrides and sandbox support. Interfaces were inspected
against CLI 0.154.0 and current official documentation; runtime validation is deferred.

```sh
python3 scripts/symphony-models.py
scripts/symphony-dispatch.sh builder high /absolute/spec.md /absolute/repo lane --model MODEL_ID
scripts/symphony-dispatch.sh scout ask @/absolute/brief.md /absolute/repo facts --model MODEL_ID --effort auto
scripts/symphony-status.sh
```

`MODEL_ID` is an ID returned by live discovery, not a Symphony alias. Without an explicit
model or `SYMPHONY_MODEL`, the dispatcher selects the catalog's sole recommended default
and labels the route provisional. It never falls back from an unavailable explicit
selection. Native role selection and evidence-led routing remain conductor
responsibilities; the CLI runner does not pretend to judge model intelligence.

See [CLI reference](skills/symphony/references/cli.md) for per-role overrides, dry runs,
repair attempts, outcome records and limitations.

## Discipline without unnecessary overhead

Keep small work solo. Scope delegates narrowly, avoid overlapping writes, and load only
relevant [Score](score/OPERATING.md) drills. Inspect source-bound evidence; repeat checks
when source, inputs or environment change, not merely because another agent ran them.
Lower-model returns need a frontier reviewer, not necessarily another vendor.
Only the conductor performs authorized landings and external mutations.

**Implemented but behaviorally unvalidated.** No mock processes, synthetic catalogs,
simulated tasks or benchmark sweeps were used for this update. There are no measured
quality, reliability or token-savings claims. Assess later on
[real work](skills/symphony/references/real-work-assessment.md); that is not an install,
merge or usability gate. Future releases need no source update while host discovery and
invocation interfaces remain compatible; breaking host APIs may need adapter maintenance.

MIT. Optional Score hooks remain host-specific and opt-in.
