---
name: safe-refactoring
description: Execute behavior-preserving code restructuring — establish a test safety net first, apply the smallest mechanical transformations in sequence, verify after each, and refuse refactors that lack the coverage to be done safely. Trigger this when the user asks to "refactor", "clean up", "simplify", "restructure", "extract", or "rename" existing working code, or when you initiate a structural improvement yourself. Do NOT trigger for changes meant to alter behavior (that's a feature/fix — use task-planning), or for diagnosing why code is broken (use debugging-methodology) — a refactor by definition starts from green.
---

# Safe Refactoring

A refactor changes structure and preserves behavior — both halves are the definition. Without
a way to PROVE behavior is preserved, you are not refactoring; you are rewriting and hoping.

## Step 0: Define the behavior contract

State in one or two lines what must be true before and after: "all existing tests pass; the
public API of `billing/` is unchanged; the CLI output is byte-identical." This contract is
what "safe" means for this refactor. If any behavior IS allowed to change, that part is not a
refactor — split it out (Step 4).

## Step 1: Establish the safety net BEFORE touching anything

1. Run the existing tests over the affected code. Record the baseline (green, or which
   failures are pre-existing).
2. Assess whether the tests actually cover the code you'll restructure: run coverage over the
   affected files, or inspect — do the tests exercise the branches you're about to move?
3. **Insufficient coverage → write characterization tests first.** These capture what the
   code DOES today (not what it should do): feed representative inputs, assert the actual
   current outputs. For messy code, golden-master style works: capture today's output for a
   corpus of inputs into fixture files, assert future output matches byte-for-byte.
4. Characterization tests are committed/verified BEFORE the first structural edit — they are
   the net; a net installed after the fall is decoration.

## Step 2: The refuse/defer rule

Refuse (or defer pending tests) when ALL of: the code has no meaningful coverage, AND its
behavior can't be cheaply characterized (nondeterminism, heavy I/O entanglement, no way to
run it), AND the restructuring is more than mechanical. Say exactly that:
> "This refactor isn't safe yet: `dispatch()` has zero coverage and side-effects I can't
> capture in a harness. I can (a) write characterization tests first (~N tests), or (b) limit
> to mechanical renames only. Which?"

Refusing a risky refactor is a correct deliverable. A "successful" blind rewrite is a defect
with a delay on it.

## Step 3: Smallest transformations, verified individually

1. Decompose into named mechanical steps — rename; extract function/module; inline; move;
   change signature (with all call sites); replace conditional with early return. One step at
   a time.
2. After EACH step: run the affected tests (the verification-loop rhythm). Green → next step;
   red → the step itself is the suspect, fix or revert it before anything else.
3. Prefer tool-assisted transformations (LSP rename, IDE extract) over hand edits — then grep
   for what tools miss: string references, docs, templates, reflection, serialized names,
   SQL, config keys.
4. Order steps so the tree compiles between every pair — never a step that requires step N+1
   to build.

## Step 4: No mixed cargo

If you discover an actual bug mid-refactor: do NOT fix it inside the refactor. Note it, finish
(or pause) the refactor to a verified state, then fix the bug as its own change with its own
regression test. A diff that both moves code and changes behavior cannot be reviewed for
either property. Same for improvements: new features never ride along in a refactor diff.

## Step 5: Prove the contract

Full affected suite green; baseline failures unchanged; and check the contract from Step 0
directly (API surface diff, byte-compare the golden outputs). Review the diff explicitly
asking one question per hunk: "could this hunk change behavior?" Any hunk answering "yes"
that isn't a pure signature-propagation gets scrutiny.

## Worked example

Task: "Clean up `report.py` — 600 lines, one god function."

- Contract: CLI output byte-identical for all supported flags; tests stay green.
- Safety net: only 2 tests exist, covering ~20%. Write a golden master: run the CLI over 8
  representative fixture inputs (incl. empty file, unicode, flag combinations), save outputs
  to `tests/golden/`. Now every future step is checked against reality.
- Steps: (1) extract `parse_args` → golden green; (2) extract `load_rows` → green;
  (3) extract `render_table` → RED: one golden diff — a `.strip()` was lost in the move;
  restore it, green (the net just paid for itself); (4) move helpers to `report/lib.py` →
  green; (5) found an actual bug (crash on zero rows) → NOTED in report, not fixed here.
- Deliver: structure changed, goldens byte-identical, bug reported separately with a
  suggested regression test.

## Done when

The behavior contract from Step 0 is verified by executed tests (including any
characterization tests written first, not after); every transformation step ran green before
the next began; the diff contains zero intentional behavior changes; and any bugs discovered
are reported separately — not silently fixed in, and not silently left unmentioned.
