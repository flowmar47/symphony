---
name: self-consistency-check
description: Check interacting requirements and edge cases before committing to a consequential design. Use a bounded constraint sweep and frontier review, respecting host delegation restrictions. Skip elaborate checks for trivial tasks; use code-review for existing diffs.
---

# Self-Consistency Check

Writing every constraint and edge case down makes a cross-term conflict *visible*; it does not
make it *noticed*. A weaker model can read a complete list and still miss that requirement 3
breaks edge case 7 — because noticing the interaction requires holding both in mind at once,
which is exactly the single-pass depth that doesn't transfer. This skill replaces that depth
with **procedure**: enumeration (which a weaker model does reliably) forced into combination
(which it doesn't do spontaneously). Run it on a plan/design/spec before you build.

## Technique 1: Pairwise constraint sweep (always, for >3 constraints)

1. List every constraint, requirement, and known edge case and number them C1..Cn. Pull them
   from the spec, the plan, and your assumptions log — don't rely on memory.
2. Build the grid. Down the side: each constraint. Across the top: each *other* constraint it
   could plausibly interact with, plus each edge case. For every plausible pair (Ci, Cj), write
   one of: **compatible** (one clause why) or **CONFLICT** (name it).
3. Rules that make it real, not ritual:
   - Do not skip a pair because it "feels fine" — that feeling is the miss you're hunting.
   - Bound it to *plausible* interactions, not a blind N² (that's ceremony); but when unsure
     whether a pair interacts, include it — the cost of a filled cell is one line.
   - Every CONFLICT is either resolved in the design now, or logged as an explicit open
     decision. A found-but-unresolved conflict is still a win — it's a bug caught pre-code.

## Technique 2: Fresh-context cold read (for interacting/high-stakes designs)

You miss the conflict because you're anchored on the path that produced the design. Someone who
never walked that path is structurally better positioned to see it.

1. When permitted, use an appropriate frontier reviewer through native delegation.
   Give it the requirements and artifacts, not a preferred verdict. A capable frontier
   conductor may instead perform a distinct deliberate review pass. Do not bypass host
   restrictions through a CLI agent. If neither option is available, mark review pending.
2. **Withhold your reasoning trace.** Do not tell it what you were thinking or why; that's the
   anchor you're trying to escape. Hand it the reasoning and it inherits your blind spot.
3. Ask exactly: "Which two statements here cannot both be true? Which requirement has no
   handling for which edge case? What does this design assume that it never states?"
4. Treat what it finds as findings to resolve, not opinions to weigh.

## Technique 3: N-version divergence (for the hard kernel)

Parallelism substitutes for depth on the one part that matters most.

1. Identify the hard kernel (problem-framing / §15.1) — the ~20% that decides the outcome.
2. Only when authorized and justified, compare at most two candidate trials per task
   class per invocation on genuine work. Keep their contexts separate and include
   frontier review and integration in total measured usage. Do not make a comparison
   a prerequisite for using or publishing a provisional route.
3. Diff the results. Agreement alone is not proof. **Where they diverge** is the
   load-bearing, uncertain decision — the exact spot a single pass would have committed to
   blindly. Investigate every divergence; often one branch honored a constraint the others
   dropped, which tells you both the right answer and which constraint was slippery.

## Worked example

Design: a "share link" feature. Constraints gathered: C1 links expire after 7 days; C2 links are
revocable instantly; C3 access is logged for audit; C4 anonymous (unauthenticated) users may
open a link; C5 GDPR — a user can delete their account and all associated PII.

- **Sweep** finds what the list alone hid: (C3 × C5) — audit logs record who accessed a link,
  but account deletion (C5) must purge PII, and access logs of *the deleted user's* links are
  PII → CONFLICT: the audit-retention policy and the deletion guarantee are unspecified together.
  (C4 × C3) — anonymous access logged how? no user id exists → what does "who accessed" even
  mean → underspecified. Neither conflict is visible staring at C1–C5 as a list; both surface
  the instant you fill the (i,j) cells.
- **Cold read** subagent, given only the spec, asks: "C2 says instantly revocable, C1 says
  7-day expiry — is a revoked link's record kept until day 7 or purged immediately? The spec
  never says." A third gap, caught by the un-anchored reader.
- Outcome: three interaction gaps found and resolved (or logged as decisions) before a line of
  code — instead of shipping the happy path and discovering the GDPR conflict in an audit.

## Done when

For the design under check: a pairwise sweep grid exists with every plausible pair marked
compatible-or-conflict; every conflict is resolved or logged as an explicit open decision;
for interacting/high-stakes designs an appropriate frontier review ran or is explicitly pending; and
for the hard kernel, either comparison was unnecessary/deferred (say so) or authorized
bounded attempts were diffed and every divergence investigated. Then hand the consistent
design to task-planning / builder.
