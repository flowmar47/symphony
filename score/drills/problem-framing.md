---
name: problem-framing
description: Shape a problem before solving it — check the premise (XY problems, false dichotomies), find the canonical name for the problem shape, locate the hard kernel, and factor fuzzy asks into orthogonal decisions. Trigger this BEFORE solving whenever a request specifies a mechanism rather than an outcome ("add a retry here"), offers a this-or-that choice ("should we use A or B?"), poses a fuzzy design/diagnostic question, or feels like something that must have been solved a thousand times before. Do NOT trigger for turning an already-well-framed build request into an ordered plan (that is task-planning, which runs AFTER this) or for choosing between candidates you've already scoped (architecture-decisions). This skill decides whether you're solving the right problem in the right frame; its successors decide how.
---

# Problem Framing

Weaker models answer the question as handed to them. The frame — what's actually being asked,
what shape the problem is, where the difficulty lives — is accepted without examination, and a
perfectly-executed answer to the wrong frame is worthless. Run these four moves, in order,
before solving anything non-trivial. Total cost: a minute. Then commit to the frame and solve.

## Move 1: Check the premise — once, cheaply

- **XY problem tell:** the request names a *mechanism*, not an *outcome* ("add a retry here",
  "make this a singleton"). The stated mechanism may be a poor path to the unstated goal.
  Response: deliver what was asked AND name the suspected goal with a sturdier path in one
  line — "this adds the retry; if the underlying goal is zero lost orders, an outbox pattern
  is sturdier — say the word."
- **False dichotomy tell:** "A or B?" Spend one beat checking for a dominant option C. If C
  exists, present it as an option — and still answer A-vs-B on its merits. Never refuse the
  question that was asked.
- **Discipline:** question the frame exactly ONCE. If the user reaffirms their frame, execute
  it fully and drop the reframe. Relitigating a settled premise is nagging, not insight.

## Move 2: Name the problem

Strip the problem to one sentence with the domain nouns removed, and ask: **what is the
canonical name for this shape?**

- "Many workers all retry at the same instant" → thundering herd.
- "Check if it exists, then create it" → TOCTOU race / upsert problem.
- "The same message may arrive twice" → idempotency.
- "One query per row of the parent query" → N+1.
- "Two systems each think they're primary" → split brain.

If the shape has a name, it has a literature: known solutions AND known pitfalls. Solving a
named problem from scratch reinvents the bugs along with the wheel. Adopt the canonical
solution unless a real constraint forbids it — and name that constraint explicitly when you
deviate. If you can't find a name after a genuine attempt, note that: truly nameless problems
deserve more design caution.

## Move 3: Locate the hard kernel

Most tasks are ~80% mechanical, ~20% genuinely hard — and the outcome is decided by the 20%.
Triage each part with one question: **"could I write this straight through without
backtracking?"**

- Yes → mechanical. Execute cheaply, later.
- No — you can't yet see the solution's shape → that's the kernel. It gets solved FIRST, with
  full explicit reasoning (candidates, assumptions, devil's advocate), before any boilerplate
  is typed.

If you finish and nothing ever made you slow down, either the task was trivial or you missed
the kernel — re-scan before delivering.

## Move 4: Factor fuzzy asks into orthogonal decisions

A fuzzy problem ("make our exports better") is usually 2–4 independent decisions tangled
together (format? delivery mechanism? sync-vs-async? permissions?). List the axes; confirm
they're independent (a choice on one doesn't force a choice on another); decide or ask per
axis. A question that seemed vague becomes 3 small crisp ones — and the user can answer each
with one word.

## Worked example

Request: *"Should we use Redis or Postgres for the job queue?"*

- Move 1 (premise): dichotomy tell → one beat for C: the codebase already runs on Postgres and
  the volume is ~200 jobs/hour. A dedicated queue (C: keep it in Postgres with SKIP LOCKED —
  or D: a managed queue) may dominate. Present C, still answer A-vs-B.
- Move 2 (name): the shape is a *work queue with at-least-once delivery* — canonical patterns:
  `SELECT ... FOR UPDATE SKIP LOCKED` (Postgres), Redis streams, SQS. Known pitfalls attached
  to each: visibility timeouts, poison messages, redelivery.
- Move 3 (kernel): the hard part isn't the store — it's **failure semantics** (what happens when
  a worker dies mid-job). That decision gets the explicit reasoning; the client library choice
  is mechanical.
- Move 4 (axes): (a) delivery guarantee needed, (b) throughput, (c) operational budget for a
  new stateful service. Three crisp questions instead of one vague one.
- Outcome: "At 200 jobs/hour with Postgres already deployed: SKIP LOCKED queue in Postgres, no
  new infra; the real decision is at-least-once + idempotent handlers (named pattern), here's
  that design. If you specifically want Redis anyway, it's fine — say so and I'll build that."

## Done when

The premise has been checked exactly once (and any reframe offered in one line, not litigated);
the problem's canonical name is identified or its absence noted; the hard kernel is named and
scheduled first; a fuzzy ask is factored into independent axes each decidable in one word — and
you can state, in one sentence, the frame you are now committing to solve. Then hand off to
task-planning / architecture-decisions to execute within that frame.
