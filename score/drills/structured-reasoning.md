---
name: structured-reasoning
description: A step-by-step reasoning protocol for problems that exceed one intuitive step — generate and compare candidates, track assumptions, reason backward or from a minimal case when stuck, sanity-check intermediates, and run a mandatory devil's-advocate pass before finalizing. Trigger this the moment a problem is novel, high-stakes, involves multiple interacting constraints, requires arithmetic/counting/state-tracking, or you're unsure what the next step is. Do NOT trigger for problems too large to hold in working memory (use extended-problem-solving, which externalizes to disk) or for routine one-step answers. This skill is for thinking a hard thing through in-context; its sibling is for thinking a huge thing through on paper.
---

# Structured Reasoning

Weaker reasoning fails in three predictable ways: skipped steps, unexamined assumptions, and
committing to the first plausible approach. This protocol makes each failure procedurally hard.
Do the steps visibly (in text or notes) — silent multi-step reasoning drops steps unnoticed.

## Step 1: Decide if this needs explicit reasoning

Answer directly ONLY if all hold: solved this exact shape before, one step reaches it, wrong is
cheap. Otherwise reason explicitly — any one triggers it: novelty; high stakes; multiple
interacting constraints; ANY arithmetic/counting/indexing/state-tracking; or you don't know the
second step. When in doubt, reason explicitly — it's cheap insurance.

## Step 2: Generate 2–3 candidates before starting any

One candidate is a reflex, not a decision — and reflexes commit you to the first
plausible-but-wrong path. For each candidate: one line of mechanism. Compare on explicit
criteria (correctness first, then simplicity, failure modes, reversibility). Pick, and write
one line on why over the runner-up. If you genuinely see only one approach, spend 30 seconds
forcing a second — "what if I did the opposite / did nothing / did it backward?" — before
proceeding.

## Step 3: Maintain a visible assumptions list

Write assumptions as you make them: "assuming input is pre-sorted", "assuming single writer",
"assuming the ID is unique". Keep the list in view. Rule: when a conclusion feels off or an
intermediate surprises you, check the ASSUMPTIONS first — a wrong conclusion is usually a wrong
assumption, not broken logic. Test the load-bearing ones instead of trusting them.

## Step 4: When forward reasoning stalls, switch technique

- **Backward:** write the desired end state; ask "what must be true one step before this?";
  chain back to now. Best when the goal is crisp and the path isn't.
- **Minimal case:** strip to the smallest non-trivial instance (n=1, one field, no
  concurrency); solve THAT completely; then generalize. A solved small case is a foothold; a
  half-solved big case is a swamp.
- **Concrete example:** push one specific real value through by hand. Stuck abstract reasoning
  usually unsticks the moment a real number moves through it.

## Step 5: Sanity-check every intermediate conclusion

Don't wait for the end. One line per intermediate:
- Order of magnitude — is the number even plausible?
- Boundary — does it hold at 0, 1, and the max?
- Invariant — does what must always be true (count conserved, total unchanged, sum
  non-negative) still hold?
A failed check here costs one line; a bad intermediate carried to the end costs the whole chain.

## Step 6: Mandatory devil's-advocate pass before finalizing

Never finalize a non-trivial answer without trying to break it:
1. State what would prove it WRONG — the specific input/case/condition that fails it.
2. Check that case.
3. Probe the edges (empty, boundary, huge), your least-certain assumption, and every step you
   labeled "probably fine".
If you can't build a falsifier, say so — but try hard first. This pass catches the confident-
wrong answer that would otherwise ship.

## Worked example

Problem: "Pick a rate-limit algorithm for the API; must allow short bursts but cap sustained
rate."

- Step 1: multiple interacting constraints (burst vs sustained) → reason explicitly.
- Step 2 candidates: (A) fixed window — mechanism: count per clock-minute; (B) sliding window
  log — timestamp per request; (C) token bucket — refill at sustained rate, bucket depth =
  burst. Compare: A is simplest but allows 2× burst at window edges (fails the "cap sustained"
  intent); B is exact but stores every timestamp (memory cost); C allows configured burst AND
  caps sustained, O(1) state. Pick C over B: meets both constraints at lower cost.
- Step 3 assumptions: "clock is monotonic per node"; "limit is per-user not global" — flagged.
- Step 5 sanity: bucket depth 10, refill 1/s → a client can send 10 instantly then 1/s
  sustained. Boundary check at depth=0: next request waits ~1 s. Plausible. Invariant: tokens
  never exceed bucket depth — holds.
- Step 6 devil's advocate: what breaks it? Multi-node deployment — per-node buckets allow N×
  the limit (the assumption "per node" from Step 3 is the crack). Falsifier found → note it:
  "C is correct per-node; needs shared state (Redis) if the limit must hold across nodes." Ship
  the answer WITH that caveat instead of shipping it falsely absolute.

## Done when

The approach was chosen from 2–3 compared candidates; assumptions are listed and the
load-bearing ones checked; intermediate results passed a magnitude/boundary/invariant check;
and a devil's-advocate pass has either failed to break the answer after a real attempt or
surfaced a caveat that is now stated in the answer.
