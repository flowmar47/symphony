---
name: course-correction
description: >-
  Recognize mid-task that the current APPROACH is wrong and execute a disciplined stop-revert-replan instead of accumulating patches. Trigger this when any alarm fires during ongoing work: your last two changes each fixed the previous change's symptom; the design keeps growing special cases; you're fighting or monkey-patching the framework; a "small fix" now spreads across many files; you can't explain why a line exists beyond "it made the error go away"; three attempts have failed on the same error; or you catch yourself thinking "I've come too far to restart". Do NOT trigger for a single reproducible bug with a working approach (use debugging-methodology) — this skill is for when the plan itself is the bug.
---

# Course Correction

The discipline of stopping. Failed approaches are cheap if abandoned early and ruinous if
defended. Code is cheap to rewrite from correct understanding; understanding is what the
failed attempt bought you — keep it, discard the code.

## Step 1: Recognize the alarms

Treat ANY of these as an alarm, not background noise:

1. **Patch stacking** — change N exists to fix what change N-1 broke.
2. **Growing exceptions** — "...except for POSTs, and except admin users, and except...".
3. **Fighting the framework** — overriding internals, monkey-patching, copy-pasting library
   code to force your approach through.
4. **Spreading diff** — the "small fix" touches 8 files and you can't say where it stops.
5. **Unexplainable state** — your honest answer to "why is this line here?" is "the error
   went away".
6. **Three strikes** — 3 failed attempts on the same failure.
7. **Sunk-cost narration** — the thought "too far in to restart" is itself the strongest
   signal that restarting is cheaper than continuing.

Rule: the second workaround stacked on a first is an automatic alarm — the real cause is
upstream of both.

## Step 2: Freeze

No further edits toward the current approach. Not one more "quick try". The next keystrokes
are documentation, not code.

## Step 3: Snapshot knowledge, not code

Write down, in a note or message:
- The goal (re-read the original request — it has drifted in your memory).
- Approaches tried, and what each attempt REVEALED (the constraint you didn't know, the
  behavior that surprised you).
- What is now known to be true / known to be false / still unknown.

This snapshot is the asset the failed work purchased. Without it, the revert wastes everything.

## Step 4: Revert to last known-good

`git stash`, `git checkout -- .`, or delete the scratch files. Keep the snapshot; discard the
patches. Exception: individual pieces that are independently correct and verified (a test you
wrote, a helper that works) may be kept — but only pieces you can justify in isolation.

## Step 5: Re-plan from discovered constraints

The new plan MUST explain why the old approach failed. If it doesn't, you are about to repeat
the same approach with different syntax. Check the new plan against every constraint listed in
the snapshot before writing code.

## Step 6: Escalate when scope changed

If the new plan changes scope, cost, or the deliverable itself, tell the user BEFORE executing —
one short paragraph: what didn't work, why (the discovered constraint), what you propose
instead. A clear "here's what I ruled out and why the approach must change" is a legitimate
deliverable; a fourth blind patch is not.

## Step 7: Correcting already-delivered mistakes

If you discover a defect in work you already reported as done: say so immediately and plainly
("the earlier fix misses case X — correcting now"), fix it, re-verify, re-report. Never
quietly fold the correction into the next unrelated diff.

## Worked example

Task: add per-user rate limiting to an API.

Attempt 1: decorator storing counters in a module-level dict. Test fails — counters reset
every deploy and are per-worker. Patch: move dict behind a lock. Still per-worker. Patch 2:
pickle counters to disk on shutdown. Now tests are flaky under parallel workers.

Alarm fired: patch 2 exists to fix patch 1's symptom (patch stacking) — and honestly, the
disk-pickle line only exists because "the test went away".

- Freeze. Snapshot: "Goal: per-user rate limit across 4 workers. Learned: state must be
  shared across processes → in-process storage is disqualified, not fixable. Unknown: is
  Redis available? (check lockfile — yes, used for sessions)."
- Revert both patches. Keep the rate-limit test — it's independently correct.
- New plan, which explains the failure: counters live in Redis (`INCR` + `EXPIRE`, atomic,
  shared across workers). The old approach failed on a structural constraint, not a bug.
- Result: 15 lines, tests pass under parallel workers. Total cost of the revert: the snapshot
  paragraph. Cost of NOT reverting: a pickle-based distributed-state system defended forever.

## Done when

The dead-end code is reverted; the knowledge snapshot exists in writing; the new plan names the
discovered constraint that killed the old approach; the user has been informed if scope or
deliverable changed; and work has resumed under the new plan — or the written ruled-out
summary has been delivered to the user as the honest current state.
