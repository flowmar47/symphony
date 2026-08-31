---
name: extended-problem-solving
description: >-
  Externalize reasoning to a scratchpad file for problems too large to hold in working memory — a persistent record of candidate approaches, eliminated branches and WHY they were eliminated, open questions, and current best hypothesis, updated as understanding evolves. Trigger this when a problem has more moving parts or branches than you can track in-context: multi-day investigations, complex design with many interacting subsystems, a debugging hunt across many hypotheses, or any reasoning you'll need to resume after a context break. Do NOT trigger for problems solvable in one sitting in-context (use structured-reasoning). The distinction: structured-reasoning thinks in the conversation; this skill thinks on disk because the conversation can't hold it.
---

# Extended Problem Solving

Some problems have more branches than working memory has slots. Held in-context, they cause the
signature failures: re-exploring a branch you already killed, half-remembering why you rejected
something, and losing the thread across a context break. The fix is a scratchpad on disk that
IS your working memory — you offload to it and re-derive from it rather than from recollection.

## Step 1: Open the scratchpad immediately

Create `REASONING.md` (scratchpad dir or repo root; not committed unless asked). Structure —
all sections present from the start:

```markdown
# REASONING — <problem>

## Problem statement
<the actual question, precisely; refine it as it sharpens>

## Current best hypothesis
<the leading answer/approach right now — one paragraph, updated as it changes>

## Candidate approaches / branches
- [ACTIVE]   B1: <approach> — status, what's promising
- [KILLED]   B2: <approach> — ELIMINATED because <specific reason/evidence>
- [OPEN]     B3: <approach> — not yet explored

## Confirmed facts
<things established with evidence — each with how it was confirmed>

## Open questions
<what's unresolved, ranked by how much it would unblock>

## Decisions
<choices made and why>
```

## Step 2: Record eliminations with their reason — always

The highest-value entries are the KILLED branches. When you rule something out, write WHY with
the specific evidence: "B2 (in-memory cache) killed — 4 nodes, state must be shared; confirmed
per-node state allows 4× the limit." Without the reason on disk, you WILL wander back into a
dead branch an hour later and re-walk it. The reason is what makes the elimination permanent.

## Step 3: Update as understanding evolves

- New fact confirmed → Confirmed facts, with how.
- Branch explored → flip its status, record the outcome.
- Best hypothesis changes → rewrite that section (don't just append; the current best must be
  unambiguous at a glance).
- Update at every meaningful move, not in one batch at the end — the scratchpad is only a
  memory if it's current.

## Step 4: Re-derive, don't half-remember, on return

When you come back to a branch (after a context break, a compaction, or switching away and
back): RE-READ its scratchpad entry and re-derive from the confirmed facts. Do not proceed from
a fuzzy recollection of "where I was" — that recollection is exactly what's unreliable at this
scale, and trusting it is how contradictions creep in. The file is authoritative over memory
wherever they disagree.

## Step 5: Stop conditions — recognize grind and switch

Watch for these and change strategy rather than grinding:
- **Circular reasoning:** you're revisiting a branch whose KILLED entry you wrote yourself.
  Stop — it's already answered; read the reason.
- **Diminishing returns:** the last three updates added detail but didn't move the best
  hypothesis or close an open question. The current strategy is exhausted — switch technique
  (backward reasoning, minimal case, or get more evidence) or escalate to the user.
- **All branches killed:** the problem as framed has no solution → the Problem statement or an
  assumption is wrong. Re-examine the framing, not the branches.
- **Thrashing:** best hypothesis flipping back and forth between two options → you're missing a
  distinguishing fact. Name it in Open questions and go get THAT, instead of re-arguing.

## Worked example

Problem: intermittent data corruption in a pipeline, cause unknown, spans ingestion →
transform → store across three services.

- Scratchpad opened. Branches: B1 ingestion race, B2 transform off-by-one, B3 store
  serialization, B4 clock/ordering.
- B2 explored → KILLED: "transform is pure, property-tested over 10k inputs, no corruption
  reproduced — eliminated with evidence." (Recorded so it's never re-opened.)
- Confirmed fact: "corruption only on records processed within 100ms of each other — confirmed
  from log correlation." This kills B2/B3 further and promotes B1.
- Best hypothesis rewritten to B1 (concurrent ingestion). Open question: "does the ingestion
  queue guarantee per-key ordering?" — ranked top, most unblocking.
- Context compaction happens. On return: re-read scratchpad, re-derive from Confirmed facts —
  no time lost, no re-walking B2. Answer the open question (queue does NOT guarantee per-key
  order) → B1 confirmed, root cause found.
- Stop condition never triggered because eliminations were permanent; contrast the without-
  scratchpad run, which re-investigates the pure transform twice.

## Done when

The scratchpad holds the current best hypothesis, every branch with an ACTIVE/KILLED/OPEN
status, and every elimination paired with its evidence; you re-derived from it (not from
memory) after any context break; and you reached either a confirmed solution or an explicit
stop-condition call (reframe / switch strategy / escalate) rather than grinding a dead branch.
