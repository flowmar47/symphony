---
name: task-planning
description: Parse a request and produce an ordered execution plan before any code is written. Trigger this at the START of any new task — when the user asks to build, implement, add, create, migrate, or refactor something; when a request spans multiple files or steps; when a request contains vague scope words ("the configs", "handle errors etc."), ordering instructions, or prohibitions; or whenever you notice you don't know what you'd do second. Do NOT trigger for mid-task failures (use debugging-methodology), for choosing between two designs you've already scoped (use architecture-decisions), or for single-line edits you can hold entirely in your head.
---

# Task Planning

Turn a request into a verified understanding and an ordered, checkable plan — before touching
code.

## Step 1: Parse the request

Answer these four questions in writing (a todo note or a short message):

1. **Deliverable:** what artifact exists when you're done — a file, a passing test, a diff, a
   prose answer? One sentence. If you can't write the sentence, the request is ambiguous —
   go to Step 3.
2. **Explicit constraints:** scan for named technologies, paths, formats, prohibitions ("no new
   dependencies"), and process instructions ("one file at a time", "ask before committing").
   List them. Process instructions are requirements with the same weight as functional ones.
3. **Implicit requirements** by deliverable type:
   - New endpoint → input validation, auth, error responses, ≥1 test.
   - Bug fix → regression test that fails before the fix, passes after.
   - Script → handles missing/malformed input, exits non-zero on failure.
   - Refactor → behavior preserved, existing tests pass, no public API change unless stated.
4. **Verification condition:** what command or observation proves it works? Define it now —
   it shapes the implementation. No plan is complete without it.

## Step 2: Detect hidden scope

- "Just / simply / quick" = the user's effort prediction, not permission to cut corners.
- Symptom described, not a change ("login is broken") → the deliverable is a **diagnosis**;
  report findings, don't jump to the first plausible fix.
- Solution named, not a problem ("add a retry here") → implement it, but if inspection shows
  it won't fix the underlying issue, say so in one line while delivering.
- Plurals and "etc." → enumerate the concrete list you believe is in scope and state it.

## Step 3: Ask vs. proceed

**Ask** (max 2–3 batched questions, each with your recommended default) only when ALL hold:
- The ambiguity changes WHAT you'd build, not just how; AND
- The wrong choice is expensive to reverse (schema, public API, deletion, external side
  effects, >~30 min of work in one direction); AND
- The codebase/conversation cannot answer it. Never ask what a grep can answer.

**Otherwise proceed** and state the assumption in one line at delivery:
> "Assumed per-day grouping, not per-run — flip `GROUP_BY` if wrong."

## Step 4: Decide whether to plan formally

**Dive in** (no written plan) when ALL: 1–2 localized edits, whole change fits in your head,
verification is one command, revert is cheap.

**Write a plan** when ANY: 3+ files or a module boundary crossed; a schema/public-interface
decision embedded; migration-shaped repetition; user-specified ordering; or you're unsure what
step two is.

## Step 5: Build the plan

1. Steps in dependency order: types/schema → pure logic → I/O adapters → interfaces → glue.
2. Each step ends with its own check (compile / import / unit test / run).
3. **Do the riskiest step first** — the unfamiliar API, the unverified assumption. If it fails,
   the plan changes while it's cheap.
4. A step describable only with "and" gets split.
5. 4+ steps → write the plan down (todo list or file). Head-only plans mutate silently.

## Step 6: Scope each candidate piece — build / defer / refuse

1. Stated or implicit requirement → **build**.
2. Needed for the stated thing to actually work (error path, the edge case the data will
   certainly contain) → **build**.
3. Plausible future need ("might want multiple providers") → **defer**, with a one-line note:
   "skipped X; add when Y".
4. Contradicts the request (framework where a script was asked) → **refuse**, one line, with
   reason.

## Worked example

Request: *"Write a script that syncs new rows from table A to table B nightly."*

- Parse: deliverable = runnable script; verification = run twice against a seeded test DB, row
  counts correct and no duplicates.
- Implicit: idempotency (cron re-runs), non-zero exit on failure, log counts.
- Build: sync + idempotency + exit codes + count logging.
- Defer: config file for table names (constants + note), parallelism, metrics.
- Refuse: generic pluggable-ETL framework — "60-line script; a framework isn't warranted until
  a third table pair exists."
- Plan order: (1) query for new rows + test on seeded DB, (2) idempotent insert + re-run test,
  (3) logging/exit codes, (4) end-to-end run.

## Done when

You have written: the deliverable sentence, the constraints list, the verification condition,
any assumptions or batched questions, and (for multi-step work) an ordered plan whose first
step is the riskiest — and every stated requirement in the original request appears in the
plan or in an explicit defer/refuse note. Only then start implementing.
