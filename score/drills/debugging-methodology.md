---
name: debugging-methodology
description: Step-by-step procedure for diagnosing and fixing failures — reproduce, read, hypothesize, bisect, fix, regression-test. Trigger this whenever something does not work as expected — a bug report, a failing or flaky test, a crash, an error message, wrong output, "it worked yesterday", or unexpected behavior during your own implementation. Trigger BEFORE proposing any fix. Do NOT trigger for building new features (use task-planning) or for the moment you realize your overall approach is wrong rather than the code (use course-correction).
---

# Debugging Methodology

Fix causes, not symptoms. The procedure is sequential — skipped steps are where the time goes.

## Step 1: Reproduce (mandatory, no exceptions)

1. Make the failure happen on demand with the shortest command available. Capture the exact
   output. A fix applied to an unreproduced bug is a guess wearing a fix's clothes.
2. Can't reproduce? Then the task is information-gathering, not fixing: collect failing inputs,
   versions, environment, logs, timing. Do not theorize past the evidence you have.
3. Shrink it: smallest input, fewest components. Every component removed is a component
   exonerated.

## Step 2: Read before theorizing

1. Read the WHOLE error message and the WHOLE stack trace, literally. `KeyError: 'user_id'`
   means that key was absent in that dict at that line — start there, not at your favorite
   suspect.
2. Read the failing function completely, then read the code that produced the data it consumed.
3. Sweep the boring environmental causes FIRST — they are frequent: wrong directory, stale
   build/cache, unsaved file, wrong branch, wrong env/port, version mismatch, leftover process
   holding a port.

## Step 3: Hypothesize — falsifiably

Write the hypothesis as a sentence that an observation could prove false:
> "The handler receives None because the middleware short-circuits before auth populates it."

If you can't phrase it falsifiably, you have a mood, not a hypothesis — go back to Step 2.

## Step 4: Test ONE hypothesis with the cheapest observation

1. Choose the cheapest observation that distinguishes true/false: a print/log of the actual
   value at the suspect boundary, a debugger breakpoint, a 3-line unit test, `git bisect` when
   the failure is "used to work".
2. Prefer observing state over re-reading code: code says what SHOULD happen; instrumentation
   says what DID.
3. One change → run → observe → conclude. NEVER two speculative changes in one step: if it
   passes you won't know why; if it fails you won't know what to revert.
4. Binary-search the pipeline: output of A→B→C→D wrong? Probe at B/C first, not linearly.
5. Remove your instrumentation once it has answered.

## Step 5: Know when to abandon a hypothesis

Abandon — do not patch around — when:
- The observation came back false. State what you now know; derive the next hypothesis from
  that evidence, not from the discard pile.
- A fix "works" but you cannot explain the bug's mechanism. Unexplained fixes are bugs in
  hiding: keep digging, or explicitly deliver it labeled "empirical fix, mechanism unconfirmed".
- You're adding a second workaround on top of a first. Two workarounds = the real cause is
  upstream. Revert both, go upstream.

## Step 6: The 3-strike rule

After 3 failed fix attempts on the same failure:
1. STOP. Revert to last known-good (`git stash` / `git checkout -- .`).
2. Write down: what fails, exact error, what's ruled out, what each attempt changed and what
   happened.
3. Either form a genuinely new hypothesis FROM that write-up, or deliver the write-up itself
   as the current state. "Here's what I've ruled out" is a deliverable; a fourth blind patch
   is not.

## Step 7: After the fix

1. Add a regression test that fails on the pre-fix code (verify against the broken version if
   cheap — stash the fix, run, unstash).
2. Grep for siblings: the same bug usually lives wherever the same idiom was copy-pasted.
3. Run the full relevant suite, not just the new test. Re-run AFTER your final edit — a pass
   before the last tweak proves nothing.

## Worked example

Symptom: nightly report job produces an empty CSV since Tuesday.

1. Reproduce: run the job locally against Monday's snapshot → non-empty. Against Tuesday's →
   empty. Reproduced and narrowed to data-dependent in one step.
2. Read: no error raised. The query returns 0 rows; the writer wrote headers only.
3. Hypothesis: "The date filter excludes all rows because Tuesday's rows have timezone-aware
   timestamps and the filter compares naive datetimes."
4. Cheapest observation: print one row's timestamp and the filter bound → `2026-07-01T00:00:00+00:00`
   vs naive bound. Confirmed on first probe.
5. Fix at the origin (normalize at the ingestion boundary), not the crash site (not a
   band-aid in the report query).
6. Regression test: report over a snapshot containing aware timestamps must be non-empty.
   Grep for other naive `datetime.now()` comparisons — found one more in the billing job; flag
   it in the report.

## Done when

The failure reproduces on demand before the fix and provably not after; you can state the
bug's mechanism in one sentence; a regression test exists that fails on the pre-fix code; the
full relevant suite passes after your final edit; sibling occurrences were grepped for and
either fixed or reported.
