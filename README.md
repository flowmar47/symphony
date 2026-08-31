# Symphony

Multi-model orchestration for Claude Code with **one conductor and cheap, fast sections**.

Claude conducts: it decomposes the work, keeps the hardest and most consequential parts
for itself, and delegates the rest —

- **Builder** — [Codex CLI](https://github.com/openai/codex) (`gpt-5.6-sol`) implements
  frozen specs at three effort tiers (`medium` / `high` / `max`).
- **Scout** — [cursor-agent](https://cursor.com/cli) (`cursor-grok-4.6-xhigh-fast`) does
  fast read-only breadth: live web + recency research, cross-repo retrieval, doc
  digestion, cold second-opinion reviews.
- **Conductor** — Claude verifies every lane on the host, owns every side effect
  (commits, PRs, releases), and plays the parts nobody else should touch.

The core idea: **delegation is cheap, trust is not.** Every delegated result is advisory
until the conductor re-proves it — re-running the tests, reading the full diff, checking
scope. Known sandbox-artifact failure classes are re-tried on the host instead of being
believed either way. Landing is always conductor-only.

## What's here

```
skills/symphony/SKILL.md       the playbook the conductor loads (roles, routing, mechanics, contracts)
score/                         the Score — the methodology, self-contained:
  OPERATING.md                   ranked Prime Directives, Integrity Rules, orchestration law
  TRAPS.md                       field-proven failure catalog (read before debugging anything twice)
  PLAYBOOK.md, INTEGRITY.md, GRADING_RUBRIC.md, drills/ (26), stacks/, hooks/ (optional)
scripts/symphony-dispatch.sh   one-line lane dispatch for either seat, with a JSONL run ledger
scripts/symphony-status.sh     tail the ledger
examples/SPEC-template.md      the frozen-spec contract every builder lane receives
install.sh                     symlinks the skill into ~/.claude/skills (prints hook wiring)
```

## Install

```bash
git clone https://github.com/flowmar47/symphony && cd symphony && ./install.sh
```

Prerequisites, verified at their own homes (Symphony configures neither):
- `codex` ≥ 0.130, authenticated (`codex login`)
- `cursor-agent` (`curl https://cursor.com/install -fsS | bash`), authenticated
- Claude Code with skills enabled

Then say **"symphony"** (or "orchestrate this") in Claude Code and hand it something big.

## The routing table (short form)

| Work | Seat | Tier/mode |
|---|---|---|
| Novel / multi-constraint / unfamiliar | Builder `max` — or the conductor keeps it |
| Behavioral features with tests, audits | Builder `high` |
| Mechanical sweeps, plumbing, renames | Builder `medium` |
| Web + recency research | Scout `plan` (+web) |
| Repo/portfolio retrieval, doc digestion | Scout `ask` |
| Cold review of a diff or plan | Scout `plan` (read-only) |
| Signing, store state, deletion, money, publishing | **Conductor only** |

## Choreography

Solo → Duet (one builder lane) → Chained duet (sequential specs) → Trio (scout researches,
conductor specs, builder implements) → Counterpoint (builder writes while scout
cold-reviews the previous lane) → Tutti (parallel lanes, disjoint file ownership).

The conductor never idle-polls: while a lane runs it verifies the previous one, preps the
next spec, or advances its own hard part.

## Failure discipline

One precise fix-list resume per failed lane, then the conductor takes it over. Dead
premises kill lanes, not goals. Tier escalations happen on evidence and get recorded so
routing improves.

## Origins

Distilled from a production run: a 13-submission App Store release train + a
multi-repo feature pass conducted this exact way — Codex building at tiered effort,
every lane host-verified before landing, and the store/release surface never leaving
the conductor's hands. The scout seat runs read-only by policy until it wins a
bake-off for a write lane; that promotion path is part of the design.

Symphony is **self-contained**: the discipline it runs on ships in this repo as
**the Score** (`score/`) — ranked Prime Directives and Integrity Rules
(`OPERATING.md`), a field-proven failure catalog distilled from production runs
(`TRAPS.md`), 26 on-demand deep drills, per-stack notes, and optional enforcement
hooks for Claude Code and Cursor. The Score is deliberately model-agnostic: seats
name roles, not models, because the models will keep changing and the failure
modes will not.

MIT.
