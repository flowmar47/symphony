---
name: verification-and-review
description: The mandatory pre-delivery pass — requirements sweep, execution proof, self-review of the diff as a stranger's, and a fixed edge-case probe. Trigger this every time you are about to say "done", "fixed", "implemented", or "passing"; before committing, opening a PR, or handing work back to the user; and after the LAST edit of any change (a passing run before the final tweak proves nothing). Do NOT trigger while still diagnosing a failure (use debugging-methodology) or while still writing (use implementation-standards) — this skill is the exit gate.
---

# Verification and Review

No success claim without executed evidence. This pass is the difference between "done" and
"probably done" — and only one of those is a word you're allowed to use.

## Step 1: Requirements sweep

1. Re-read the ORIGINAL request, not your memory of it. On long tasks your recollection has
   drifted; the text hasn't.
2. List every stated requirement AND every process instruction ("no new deps", "one file at a
   time", "don't touch the schema"). Process instructions carry equal weight.
3. Check each against the deliverable. Every unmet item gets one of exactly three labels in
   your final message: **fixed now**, **deferred (with reason)**, or **pushed back (with
   reason)**. Silently dropped is not a label.

## Step 2: Execution proof

1. Run the thing: test suite, build, lint, or the actual entry point. Read the output — all of
   it, not the exit code alone.
2. Cite actual output for every load-bearing claim: "ran `cargo test` — 42 passed, 0 failed",
   never "tests should pass now".
3. Partial verification is reported as partial: "unit tests pass; integration tests not run
   (need live DB) — run `make itest` to verify."
4. If you fixed anything during this pass, RE-RUN after the last edit.
5. If you cannot execute (no env, no creds), say exactly that and hand over the command to run.

## Step 3: Edge probe

For every function/handler you wrote or changed, answer "what happens when" for each item.
Write one-word answers; test the ones answered "breaks" or "unsure":

- **Empty:** empty string / list / file / zero rows. (The most commonly unhandled case.)
- **Boundary:** exactly at the limit, one below, one above; first/last element; re-derive
  every `<` vs `<=` deliberately.
- **Absent vs. empty:** `None`/missing key is a different case from `""`/`[]`/`0` — check both.
- **Duplicates / repeats:** same item twice in input; function called twice (idempotent where
  it must be?).
- **Malformed:** wrong type, truncated file, invalid UTF-8, unexpected extra fields.
- **Encoding / special chars:** unicode (emoji, CJK, RTL), quotes and HTML/SQL metacharacters
  reaching a renderer or query, spaces in paths.
- **Time:** naive vs aware datetimes, DST, midnight/year boundaries — if code touches time at all.
- **Scale:** the loop at n=10⁶ — hidden O(n²) or per-item I/O?
- **Concurrency:** two simultaneous callers — shared mutable state? check-then-act races?
  non-atomic read-modify-write?

## Step 4: Review the diff as a stranger's

1. Read the FULL diff top to bottom in one pass without fixing anything — collect notes, fix
   after. Fixing while reading blinds you to structural problems.
2. Per hunk ask: Would I understand this cold? Does it exceed the task (drive-by edits,
   unrequested refactors — remove them)? Is anything here a guess presented as fact?
3. Hunt the signature failure modes specifically: API calls never verified against
   docs/source, requirements quietly narrowed, success claims without a run.
4. Cleanup check: debug prints gone, TODOs owned, scaffolding removed, no leftover
   instrumentation.

## Step 5: Report

- Lead with the outcome in the first sentence; the reader should know the state of the world
  after one paragraph.
- Include: verification evidence, unmet/deferred items, assumptions made, limitations with
  trigger + remedy ("handles files up to memory; switch to streaming past ~1 GB"), the exact
  command for the user to verify themselves.
- Bad news goes at the TOP, with actual output — "2 of 14 tests fail — both pre-existing on
  main, verified by stashing my changes" — never buried after successes.
- Omit: process narration, restated diffs, rejected options (unless the call was close),
  filler.

## Worked example — weak vs. correct claim

Weak: "I've implemented the export feature and it should now handle all the cases correctly."

Correct: "Export implemented in `export.py` (+ `test_export.py`, 6 tests). Ran
`pytest tests/test_export.py` — 6 passed. Edge probe: empty dataset → header-only CSV (tested);
unicode names → tested; >1 GB datasets NOT handled (loads into memory) — flag if needed.
Assumed ISO-8601 dates; say the word for locale formatting. Deferred: XLSX output (not
requested)."

## Done when

Every requirement from the original message is labeled fixed/deferred/pushed-back; the final
verification run happened AFTER the last edit and its actual output is cited in your report;
the edge probe has a written answer per item for each new function; and the diff contains
nothing you couldn't justify to a reviewer line by line.
