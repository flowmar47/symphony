---
name: predictive-execution
description: >-
  The ambient execution discipline — predict the outcome of every consequential command BEFORE running it and treat any surprise (better or worse) as a model error to investigate; choose the next action by information gain; estimate blast radius before touching anything shared. Trigger this continuously during hands-on work: before running a command/test/query whose outcome matters, when choosing among several possible next actions, and before editing anything with dependents. Do NOT confuse with verification-loop (which says WHEN to run checks — after each edit) or debugging-methodology (which owns hypothesis-testing once a failure is confirmed): this skill governs the epistemic stance around every execution — it is usually what DETECTS the failure those skills then handle.
---

# Predictive Execution

Running a command "to see what happens" is a slot machine: whatever comes out, you learn almost
nothing, because you had no expectation for reality to collide with. This skill converts every
execution into a hypothesis test, every choice of action into an information decision, and
every edit into a scoped-risk decision. It is the single highest-leverage habit for making a
weaker model behave like a stronger one during hands-on work.

## Rule 1: Predict, then run, then compare

Before every consequential command, test run, or query, **write the expected outcome first** —
one line, specific enough to be wrong: "42 tests pass", "returns 3 rows", "exits non-zero
complaining about the version", "p95 drops below 400ms".

Then run, and compare. Three cases:

1. **Match** → your model of the system is confirmed. Proceed.
2. **Worse than predicted** → your model is wrong somewhere. STOP and locate where before
   proceeding. The divergence is the most information-dense moment you'll get — it marks
   exactly where your understanding and reality part ways. Continuing past it means building
   on a model you just proved wrong.
3. **Better than predicted** — "passed, but I expected failure" — is **equally suspicious**,
   and the case weaker models always wave through. A test that passes when you expected red is
   usually not testing what you think it tests (wrong file ran, stale build, assertion
   vacuous). A bug that "fixed itself" didn't. Investigate with the same seriousness as case 2.

**Never brush past a surprise in either direction.** If you must defer investigating one,
write it down as an open question — a surprise you neither investigated nor recorded is a
defect in your understanding left armed.

## Rule 2: Choose the next action by information gain

At any point with several possible actions, ask: **"which action's outcome most reduces my
uncertainty — best discriminates between my live hypotheses?"**

- A cheap look that eliminates half the hypothesis space beats an expensive build that confirms
  what you already believe.
- Don't take actions whose outcome you can already predict with high confidence — unless
  verification IS the point (then Rule 1 applies: predict first anyway).
- Tie-break equal information gain by cost, always.
- This generalizes debugging's "cheapest distinguishing observation" to everything: which file
  to read next, which experiment to run, which question to ask.

## Rule 3: Estimate blast radius before editing anything shared

Before changing anything with potential dependents, enumerate them **mechanically, not from
recall**: grep for direct callers; look for serialized artifacts the old code produced (DB
rows, cached JSON, files, wire messages); consider consumers in other services/repos, docs,
tests, scheduled jobs. Then one step further: what depends on the dependents?

The classification that decides how careful to be: **does this thing's meaning cross a process
or persistence boundary?**

- No (a pure function with three greppable callers) → it's an *edit*: change it, update the
  callers, verify.
- Yes (a JSON field in a queue message, a DB column, a public API shape) → it's a *migration*:
  invisible dependents exist; use expand/contract or versioning, never a casual in-place change.

## Worked example

Task: "The nightly export is empty since Tuesday; fix it."

- Weak execution: run the job, stare at output, add a print, run again, tweak a filter, run
  again — five runs, no predictions, learning by slot machine.
- Predictive execution:
  1. Hypotheses: (a) query returns 0 rows, (b) rows returned but serializer drops them,
     (c) file written then overwritten. **Rule 2:** the single most discriminating observation
     is the row count at the query boundary — one log line splits (a) from (b)+(c).
  2. **Rule 1 predict:** "if (a), count=0 on Tuesday's snapshot; if not, count>0." Run →
     `count=1842`. Hypothesis (a) eliminated; model updated.
  3. Next discriminator: does the serializer receive them? Predict "serializer input len 1842"
     → run → `len=0`. Divergence located between query and serializer — reading that seam
     finds a new filter added Monday that compares naive vs aware datetimes.
  4. Fix at the seam. **Rule 3 blast radius:** the shared `to_utc()` helper being fixed is also
     used by the billing job (grep found 2 callers) — its meaning crosses a persistence
     boundary (timestamps already written). Fix is made backward-compatible; billing job's
     tests run too.
  5. Final run — predict "export = 1842 rows, billing suite green" → matches. Done in 3
     runs, every one of which either confirmed the model or located the divergence.

## Done when

Ongoing — this is an ambient discipline, not a stage. You are following it when: no
consequential command this session ran without a written expectation; every surprise (better
OR worse) was investigated or explicitly logged as an open question; next actions were chosen
for information gain, not habit; and nothing whose meaning crosses a process/persistence
boundary was changed as a casual edit.
