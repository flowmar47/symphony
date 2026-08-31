---
name: session-state-management
description: Stay coherent across a long agentic session by keeping the task's state on disk — a WORKING_NOTES.md with the task, plan, decisions, and status — updated at every milestone and re-read after any context loss. Trigger this at the start of any task likely to exceed ~30 minutes or ~10 distinct steps; immediately after noticing context compaction or a session resume; and whenever you catch yourself re-searching for something you already found or contradicting an earlier decision. Do NOT trigger for short single-sitting tasks, and do not confuse with incremental-delivery (which orders and checkpoints the DELIVERABLE) — this skill keeps the SESSION coherent regardless of what is being built.
---

# Session State Management

Your context window is unreliable storage: it compacts, truncates, and ends. Disk does not.
Anything you'd be sorry to lose goes in a file, at the moment you'd be sorry to lose it.

## Step 1: Create WORKING_NOTES.md at task start

Location: the session scratchpad directory, or the repo root if the user's workflow expects
it (never commit it unless asked). Structure — create all sections immediately, even empty:

```markdown
# WORKING NOTES — <task title>

## Task (verbatim requirements)
<paste the user's actual requirements and process instructions — not your paraphrase;
paraphrases drift and the original message may scroll out of context>

## Plan
<ordered steps, checked off as done>

## Decisions
<one line each: what was decided, and why — "IDs are ULIDs not UUIDs: sortable, spec §3">

## Status
<done / in progress / blocked, per step>

## Next action
<the exact next command or edit, written for a cold reader>

## Assumptions & open questions
```

## Step 2: Update triggers (write at the moment, not "later")

Update the file when ANY of these occurs:
1. A plan step completes or a milestone verifies → check it off, update Status.
2. A decision is made that later work must honor (naming, format, interface shape) → Decisions.
3. The plan changes direction → rewrite Plan, note why in Decisions.
4. You're about to do anything risky or slow (migration, big refactor step, long build) →
   record Next action FIRST, so a crash mid-operation leaves a resume point.
5. Roughly every 30–45 minutes of work with no other trigger → refresh Status and Next action.

## Step 3: Re-read triggers

Re-read WORKING_NOTES.md — fully, not from memory — when:
1. A context-compaction notice appears, or a session resumes.
2. You're unsure what was already decided or already tried.
3. You're about to start a new plan step (glance at Decisions so step 9 honors what step 2 chose).
4. Before writing the final delivery message (the Task section is the requirements checklist).

**Rule:** after any suspected context loss, trust the file over your recollection wherever
they disagree. The file was written at the moment of knowledge; your recollection is a
reconstruction.

## Step 4: Split across sessions instead of overextending one

End the session at a natural boundary (a checkpoint, a completed unit) rather than pushing on,
when ANY of:
1. Remaining work is clearly larger than what's been done and quality is already degrading —
   see the signs below.
2. Verification has failed 3+ times on the same criterion (grinding, not progressing).
3. Degradation signs: repeating searches you already ran, re-deriving established facts,
   contradicting the Decisions list, or instructions from the original request coming as a
   surprise on re-read.

To split: finish the current unit to a verified state, update WORKING_NOTES.md so the Next
action block is executable cold ("run `pytest tests/test_sync.py`, then implement step 5:
retry logic in `sync.py:120` per Decision 4"), and tell the user where things stand and what
the next session picks up.

## Worked example

Mid-task, a compaction notice appears during an 8-step API migration.

- Without this skill: you continue from a summarized memory, re-implement the error envelope
  you already built (differently), and step 7 contradicts the pagination decision from step 2.
- With it: you re-read WORKING_NOTES.md — Decisions says "error envelope: `{error: {code,
  message}}`, pagination: cursor-based, decided step 2"; Status shows steps 1–5 verified,
  step 6 in progress with next action "wire cursor into `/orders` handler". You resume in two
  minutes with zero re-derivation and no drift.

## Done when

WORKING_NOTES.md exists from task start and its Status/Next-action sections would let a cold
model resume correctly right now; every cross-cutting decision made this session appears in
Decisions; and at delivery, the verbatim Task section was used as the final requirements
checklist.
