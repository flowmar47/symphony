---
name: architecture-decisions
description: Choose between competing technical approaches and make design decisions with an explicit trade-off order. Trigger this when a task requires selecting among 2+ viable designs — "should we use X or Y", designing a schema, shaping a public API, choosing a storage/queue/cache mechanism, deciding whether to add a dependency, or deciding whether to introduce an abstraction. Do NOT trigger for initial request parsing (use task-planning), for line-level style questions (use implementation-standards), or when the codebase already has an established pattern for this exact problem — in that case, follow the existing pattern without deliberation.
---

# Architecture Decisions

Pick between approaches quickly, with an explicit priority order, weighted by how expensive
the decision is to reverse.

## Step 1: Check for a decision to make at all

Grep the codebase for how this problem is already solved here (existing cache? existing error
envelope? existing job runner?). If an established pattern exists, use it — consistency with
the system beats a locally better choice. Only proceed to Step 2 when the problem is genuinely
new to this codebase or the existing pattern demonstrably fails a hard requirement.

## Step 2: Generate 2–3 candidates, no more

For each candidate write three lines:
1. Mechanism, one sentence.
2. Worst failure mode — what happens when the dependency is down, input is malformed, load
   spikes.
3. What it makes hard later — the concrete thing, not "less flexible".

If you have more than three candidates, you haven't understood the constraints; re-read them.

## Step 3: Apply the trade-off priority order

Earlier beats later unless the user explicitly reorders:

1. **Correctness on known inputs** — including the edge cases this data will actually contain.
2. **Failure behavior** — prefer designs that fail loudly, early, and partially over silently,
   late, and totally.
3. **Simplicity / reviewability** — could a competent stranger understand it in one read?
4. **Consistency with the existing system.**
5. **Extensibility** — only for axes of change with concrete evidence (a second case exists or
   is scheduled). Speculative flexibility loses to simplicity, always.
6. **Performance** — only past correctness, and only where measured or obviously hot
   (per-request loop, O(n²) on unbounded n, I/O inside a loop). No restructuring without a number.

Kill any candidate that fails a hard constraint (correctness, explicit user requirement).
Among survivors, take the simplest that doesn't foreclose a *known* future need.

## Step 4: Calibrate deliberation to reversibility

- Switching later costs < 1 hour → pick the more conventional option NOW and move on. Close
  calls between good options don't matter; record the choice in one line.
- Switching later means data migration, breaking API consumers, or redone work measured in
  days → slow down; if the user's context could change the answer, ask one batched question
  with your recommendation as the default.

## Step 5: Dependency sub-decision

Adding a dependency IS an architecture decision. In order:
1. Stdlib or an already-installed dependency does it (check the lockfile, not memory)? → use that.
2. Hand-rolled version is <~50 lines with no tricky edges? → hand-roll. **Never** hand-roll
   dates/timezones, crypto, unicode handling, or parsing of established formats — these are
   always tricky.
3. Otherwise: one boring, widely-used, maintained, license-compatible library. Never a
   framework to use one function.

## Step 6: Abstraction sub-decision

Introduce an interface/base class/plugin point only when two concrete cases already exist or a
second is actually scheduled. One implementation → write the direct version and leave a
one-line note naming the upgrade path. When you break any default pattern, leave a comment
naming the constraint that forced it — the constraint, not a narration.

## Default patterns (use unless codebase or user overrides)

- Pure logic at the core; I/O (network, disk, DB, clock, randomness) at the edges, passed in.
- Errors via the language's native mechanism; fail fast on programmer errors; contextualize
  expected failures; never catch-and-continue silently.
- Persistence invariants live in the database (constraints, unique indexes, FKs), not only in
  app code.
- Validate at trust boundaries; trust internally.
- Composition over inheritance; functions over classes when no state is carried.

## Worked example

Task: "Products API is slow; add caching to product lookups."

- Step 1: grep finds `redis` in the lockfile, used for sessions. Candidate space narrows.
- Candidates: (A) Redis cache-aside, TTL 5 min. (B) In-process LRU per instance.
  (C) Materialized view refreshed on write.
- Failure modes: A — stale up to TTL; Redis outage degrades to DB (fine). B — inconsistent
  across instances after writes (there are 4 instances → correctness problem for
  post-update reads). C — write amplification, and the write path is owned by another team
  (hard constraint).
- Kill C (constraint), kill B (fails correctness at priority 1 given multi-instance writes).
- Choose A. Reversibility: swapping cache strategy later ≈ an hour → decide now, no user
  question needed. Record: "Cache-aside via existing Redis, TTL 5m, key `product:{id}`,
  invalidated on update."

## Done when

The chosen approach is written in 1–3 lines (mechanism, key parameters, why-over-runner-up),
every rejected candidate has a named reason tied to the priority order or a hard constraint,
and any expensive-to-reverse decision has either user sign-off or a stated assumption at
delivery. Then implement.
