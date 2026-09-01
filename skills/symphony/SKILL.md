---
name: symphony
description: Use when I say "symphony", "conduct", "orchestrate this", "delegate this across models", or when a task is big enough to split across Codex CLI lanes while Claude keeps the hardest parts. Multi-model orchestration — Claude conducts, Codex builds (workspace-write) and scouts (read-only with web search).
---

# Symphony — multi-model orchestration, one conductor

The primary agent — Claude in Claude Code today, whatever conducts tomorrow — is the **conductor**: it decomposes the work, keeps the hardest and
most consequential parts for itself, delegates the rest to the right model at the right
effort, verifies everything on the host, and lands the results. Delegates never commit,
push, sign, or touch release state — the conductor owns every side effect.

Symphony ships its own discipline: **the Score** (`score/` in this repo — OPERATING.md,
INTEGRITY.md, PLAYBOOK.md, TRAPS.md, 26 drills, per-stack notes, optional enforcement
hooks). The Score's rules apply to every seat: spec before delegation, evidence beats
assertion at every handoff, explicit file ownership for parallel work, bounded verdicts,
and no success claims without a host-run check. Where this file and the Score conflict,
the Score wins. Read `score/OPERATING.md` once per session on serious work; load a drill
(`score/drills/<name>.md`) when its situation arrives; pattern-match `score/TRAPS.md`
before debugging anything twice.

## The orchestra

| Seat | Engine | Modes | What it gets |
|---|---|---|---|
| **Conductor** | Claude (this session) | — | Decomposition, architecture, novel/hard debugging, anything irreversible (commits, pushes, releases, store mutations, secrets), all verification, all landings, final integration |
| **Builder** | Codex CLI (`gpt-5.6-sol`) | workspace-write | Implementation lanes against a frozen spec: features, tests, refactors, mechanical sweeps |
| **Scout** | Codex CLI read-only (`-s read-only`; web search via the account's search MCP; `SYMPHONY_SCOUT_EFFORT=low|medium|high`) | ask / plan (read-only) | Fast breadth: web + recency research, cross-repo retrieval sweeps, doc digestion, cold second-opinion reviews, large-log triage |

The scout starts **read-only by policy**, not by accident: the sandbox cannot edit. Promote
the scout to write lanes only after it wins a bake-off against the builder on that task
class, and record the promotion in this file.

**Seat health is checked, never assumed.** cursor-agent held this seat until 2026-09-01, when
its print mode proved unreliable on this bench (hangs on inherited stdin; intermittently empty
output even with `</dev/null`; still failing after `cursor-agent update`), while read-only
Codex answered every web-research probe correctly with cited URLs. The seat was retired rather
than kept behind a preflight. The dispatcher fails a scout lane on empty output instead of
recording it as done. Because builder and scout now share one vendor, a cold second-opinion
review of builder output should come from the conductor's own model (a Claude subagent), not
from another Codex lane.

### Why this seating
- The builder's strength is sustained, spec-faithful implementation with tests — give it
  closed problems with acceptance criteria.
- The scout's strength is latency and breadth — give it open questions where the answer is
  "found", not "built": what exists, what changed upstream, what do these 40 repos share,
  does this claim survive a cold read.
- The conductor's strength is judgment — so it spends its tokens on decomposition, the
  genuinely hard parts, and on *not trusting anyone*, including itself (the Score's review
  chain applies to conductor-written code too).

## Effort routing

Pick the cheapest tier that the task class has actually succeeded at before; escalate on
failure, never preemptively.

| Task class | Seat | Tier |
|---|---|---|
| Novel algorithm, multi-constraint feature, unfamiliar domain | Builder | `max` (or conductor keeps it) |
| Behavioral feature with tests, audit+fix passes, API surfaces | Builder | `high` |
| Mechanical: shortcuts, config plumbing, renames, scaffolds-by-example | Builder | `medium` |
| Web/recency research, "what is the current…" | Scout | plan+force |
| Repo/portfolio retrieval, "which repos have…", doc digestion | Scout | ask |
| Cold second-opinion review of a diff or plan | Claude subagent (a different model from the builder) | read-only |
| Anything touching signing, store state, money, deletion, or public surfaces | **Conductor only** | — |

## Invocation mechanics (verified on this bench)

### Builder — Codex CLI
```bash
# Launch (background for anything > ~2 min). Prompt via stdin heredoc; NEVER a bare
# argument without stdin redirect — codex exec blocks forever on a non-TTY without EOF.
codex exec -c sandbox_mode="workspace-write" -c approval_policy="never" \
  -c model_reasoning_effort=<medium|high|max> \
  --json -o /tmp/codex-<lane>.txt - <<EOF 2>/dev/null | grep thread.started
GOAL: <one paragraph, what done looks like>
SPEC: Read <absolute spec path> — implement exactly; report deviations.
EOF
# thread_id from the thread.started line; final report in the -o file (never parse the JSONL).
# Fix rounds: codex exec resume "<thread_id>" --dangerously-bypass-approvals-and-sandbox \
#   --json -o /tmp/codex-<lane>.txt - <"$FIXFILE"
# Reviews: -s read-only on first call; resume forces -c sandbox_mode="read-only".
```

### Scout — Codex read-only
```bash
# Web + recency research (plan): read-only sandbox, web search allowed, prompt via stdin,
# never a bare argument (codex exec blocks on a non-TTY without EOF).
codex exec --skip-git-repo-check -s read-only -c approval_policy="never" \
  -c model_reasoning_effort=medium --json -o /tmp/scout-<lane>.txt - <<'EOF' 2>/dev/null >/dev/null
READ-ONLY SCOUT LANE. Do not create, edit, or delete any file. Use web search and fetch
freely; cite the URL for every load-bearing claim; label anything not observed as INFERRED.
<research brief>
EOF
# Repo retrieval / doc digestion (ask): same command with the rule
# "Do not use web search or fetch; answer from the repository and your own knowledge only."
# Final answer lands in the -o file; the JSONL on stdout is the event log.
# Run from the directory the question is about. Empty output = failed lane, re-dispatch or take over.
```

Or use the bundled dispatcher, which wraps both and keeps a run ledger:
```bash
scripts/symphony-dispatch.sh builder <medium|high|max> <spec.md> <repo-dir> <lane-name>
scripts/symphony-dispatch.sh scout  <ask|plan> "<prompt>" <dir> <lane-name>
scripts/symphony-status.sh   # tail the ledger
```

## The spec contract (builder lanes)

Every builder lane gets a frozen spec file. Codex starts with zero context — the spec is
the whole briefing:

- **GOAL** — one paragraph of what done looks like, in user-visible terms.
- **Writable scope** — exact repos/dirs; everything else is read-only. Parallel lanes get
  disjoint scopes — no two seats edit the same file, ever. The scope must equal what the
  dispatch can actually write: a builder's write sandbox is rooted at its launch directory,
  so a spec naming four repos dispatched from one repo's cwd silently strands three —
  dispatch multi-repo work as per-repo lanes (or from a common root, accepting the wider
  blast radius the spec then has to constrain).
- **Constraints** — what must not change (versions, policy values, deps, public claims).
- **Non-goals** — the tempting adjacent work it must not do.
- **Proof** — the exact commands whose verbatim output the report must include.
- **STOP rule** — when a premise fails ("if X doesn't exist, stop and report what does").

## The verification contract (non-negotiable)

Delegate output is **advisory until the conductor re-proves it on the host**:

1. Read the full report AND `git status --porcelain` in every writable repo — scope creep
   is a finding even when the code is good.
2. Re-run the proof commands yourself. A delegate's pasted output is never evidence.
3. Known sandbox-artifact classes (Seatbelt denials, pasteboard nil in headless, AVFAudio
   `1718449215`/`fmt?`, SwiftPM nested `sandbox-exec`, simulator services unavailable) are
   **environment, not regression** — but you must prove that by running the same suite on
   the host, not by assuming it.
4. Scout research: spot-check at least one load-bearing claim against its cited source
   before acting on it. No citation → treat as unverified hypothesis.
5. Landing (branch, commit, PR, merge) is conductor-only, after verification, with
   problem-first commit messages and the attribution trailer naming every seat that played
   (e.g. `Opus 5 via Claude Code (Codex gpt-5.6-sol built, Codex read-only scouted, Claude verified)`;
   name the engine that actually answered — the ledger records it per lane).

## Choreography patterns

- **Solo** — conductor does it. Default for small work; delegation has overhead.
- **Duet** — one builder lane, conductor verifies + lands. The workhorse.
- **Chained duet** — several specs, one background command, sequential (shared machine
  resources, ordered risk). Proven shape for multi-repo sweeps.
- **Trio** — scout researches → conductor writes spec from findings → builder implements.
  Use when the spec depends on facts you don't have (upstream APIs, current versions).
- **Counterpoint** — builder implements while a Claude subagent cold-reviews the *previous*
  lane's diff, or the scout independently re-verifies the same public claims. Never on the
  same files concurrently.
- **Tutti** — parallel builder lanes with disjoint repo ownership + a scout sweep.
  Reserve for breadth (portfolio passes); state file ownership in every spec.

While any lane runs, the conductor keeps working: verify the previous lane, prep the next
spec, or advance its own hard part. Never idle-poll; land results as notifications arrive.

## Failure discipline

- A failed lane gets **one** resume with a precise fix list; after the second failure the
  conductor takes the work over directly (the Score’s 3-strike rule).
- A dead premise kills the lane, not the goal: record it, re-scope, redispatch.
- Escalate tiers on evidence ("medium produced shallow tests twice for this class"), and
  record the escalation so routing improves.
- Runaway/hung lane: check the process table before assuming progress; a silent lane with
  ~0 CPU is blocked, not thinking.

## The Score in one breath

The methodology is part of the framework, not a prerequisite: `score/OPERATING.md` holds
the ranked Prime Directives and Integrity Rules every seat obeys; `score/TRAPS.md` is the
field-proven failure catalog (pipelines that lie, premises that die, sandboxes that fake
failures, digests that hash two ways) — consult it before any second debugging attempt;
`score/drills/` are the deep procedures, loaded on demand; `score/hooks/` optionally
enforces the mechanical subset (risk guard, delivery gate, per-edit verify) in Claude Code
or Cursor. The builder→verify→cold-review chain for Standard+ work realizes the Score's
review discipline: builder lane → conductor host verification → cold review by a Claude
subagent (the scout re-verifies public claims; it does not review its own vendor's code).
