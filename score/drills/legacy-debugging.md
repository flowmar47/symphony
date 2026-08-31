---
name: legacy-debugging
description: >-
  Debug code you didn't write and can't fully trust — unfamiliar, poorly documented, or untested subsystems — using history archaeology, boundary instrumentation, minimal harnesses, and history bisection, while resisting the urge to rewrite. Trigger this when a failure lives in code that is foreign to you AND lacks reliable documentation or tests: inherited services, vendored code, an unowned module, "nobody knows how this works". For failures in code you understand and can navigate normally, use debugging-methodology instead — this skill adds the archaeology layer for when reading the code alone doesn't tell you what it's supposed to do.
---

# Legacy Debugging

In legacy code the missing artifact isn't the fix — it's the INTENT. The code tells you what
happens; nothing tells you what was supposed to happen. This skill recovers intent from
history and runtime behavior before you change anything.

## Step 1: Reproduce first — no exceptions

Same iron rule as all debugging: make the failure happen on demand with the shortest command,
capture exact output, shrink the reproduction. In legacy code this matters MORE, because you
cannot fall back on "I know what this should do" — the reproduction is your only oracle.

## Step 2: Archaeology — recover the intent

1. `git log --follow -- path/to/file` and `git blame` on the failing region. Commit messages,
   linked issues, and PR descriptions are the documentation that was never written. The
   commit that introduced a weird line usually says why.
2. Grep for the failing function's callers. How it is USED is stronger evidence of intended
   behavior than how it reads.
3. Look for abandoned intent nearby: old tests (even skipped ones), doc comments that no
   longer match the code (they describe an earlier intent — note WHEN they diverged via blame),
   config flags nobody sets.
4. **Chesterton's fence procedure:** before deleting or "fixing" code that looks wrong or
   pointless, find the commit that added it. If the commit explains it — you just learned a
   constraint. If it doesn't and no caller depends on it, note it as a candidate removal in
   your report; don't remove it as part of the bug fix.

## Step 3: Instrument boundaries — trust nothing named

1. In unfamiliar code, names lie: `validated_input` may be unvalidated; `cache` may never
   hit. Log ACTUAL values at the boundaries of the failing region — arguments in, return
   values out, state before/after — and read what's really flowing.
2. Instrument at the seams between components before instrumenting inside them: it tells you
   WHICH component misbehaves before you spend hours in the wrong one.
3. Keep a written record of confirmed facts as you go ("`parse_row` returns None for rows
   with quoted commas — confirmed by log"). In legacy work the fact list IS your growing
   documentation; it goes in your working notes and, distilled, in your final report.

## Step 4: Build a minimal harness

If the failing unit can't be invoked directly, spend the 15 minutes writing a scratch harness
that calls it with controlled input (a scratch test file or REPL script). Debugging through
five layers of the full app multiplies every observation's cost; the harness pays for itself
by the third run. The harness later upgrades into the regression test.

## Step 5: Bisect history when it "used to work"

If there is any version where the behavior was correct: `git bisect` with your reproduction
script as the oracle. Ten minutes of bisect beats hours of code reading — it hands you the
exact commit, whose message and diff explain both mechanism and intent at once.

## Step 6: Resist the rewrite

The urge to rewrite unfamiliar code is strongest exactly when you understand it least — that
correlation is the warning. Rules:
1. The fix is minimal and local. Match the file's existing style even if you dislike it —
   a mixed-idiom file is worse than a consistently old-fashioned one.
2. Every weirdness you don't understand and don't need to touch stays untouched, and goes in
   the report's findings list instead.
3. Rewrite only as an explicitly scoped separate task with the user's sign-off AND a
   characterization-test net first (see safe-refactoring) — never as a side effect of a bug fix.

## Step 7: Fix, test, document what you learned

Regression test via the Step 4 harness; run whatever suite exists. Your report includes the
recovered intent ("per commit a1b2c3, the retry exists because vendor API returns 503 during
rebalancing") — you are leaving the documentation you wished you'd found.

## Worked example

Symptom: inherited invoice service occasionally emits duplicate invoices. No docs, no tests.

1. Reproduce: replaying Tuesday's queue snapshot against a local instance → 2 duplicates,
   deterministic. Shrunk to one message replayed twice.
2. Archaeology: blame on the dedup check → commit "temp: relax idempotency check for
   migration (revert after June)" — from three years ago. Intent recovered: the check is
   deliberately weakened, and the revert never happened.
3. Instrument the seam: log the idempotency key at consume time → keys differ for identical
   messages; the key includes a timestamp. Second fact.
4. Fix: minimal — restore the strict check per the original commit, key on message ID, not
   timestamp. NOT a rewrite of the consumer, however tempting.
5. Harness → regression test (same message twice → one invoice). Report includes the history
   finding and flags two other "temp:" commits found nearby as candidates for review.

## Done when

The failure reproduces before and provably not after; the fix's mechanism AND the original
intent of the code you changed can each be stated in a sentence with evidence (commit,
caller, or log); the fix is minimal and style-matched; a regression test exists; and every
untouched weirdness you found is listed in the report rather than silently "improved".
