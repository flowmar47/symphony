---
name: verification-loop
description: >-
  The tight edit-verify cycle DURING implementation — after every meaningful change, run the fastest sufficient check before making the next change; never accumulate a batch of unverified edits. Trigger this continuously while writing or modifying code: after each function implemented, each bug-fix edit, each config change, each refactoring step. Do NOT confuse with verification-and-review, which is the one-time exit gate before claiming "done" — this skill is the per-edit rhythm that makes that final gate boring. Do not trigger for pure prose/documentation edits with nothing executable to check.
---

# Verification Loop

One verified change at a time. N unverified edits followed by one test run converts N
independent, trivially-locatable bugs into one entangled failure with N suspects. The loop
exists to keep the suspect list at length one.

## The cycle

```
edit → fastest sufficient check → green? → next edit
                                → red?  → fix NOW (suspect list has one entry)
```

**Rule: never leave the tree red while moving on to something else.** A red state you walk
away from becomes someone's (usually your own) archaeology dig an hour later.

## Step 1: Choose the fastest SUFFICIENT check per change

Match the check to what the change could have broken — no stronger, no weaker:

| Change | Sufficient check |
|---|---|
| Syntax-level edit, rename, import change | Type-check / compile only: `tsc --noEmit`, `cargo check`, `ruff check` + import |
| Logic change inside one function | That module's unit tests: `pytest tests/test_x.py -k name`, `cargo test module::`, `vitest run file` |
| Interface change (signature, schema, contract) | Consumers' tests too — grep for callers, run their suites |
| Config / env / build-system change | A real build or boot: the thing configs actually affect |
| Bug fix | The regression test (must fail pre-fix, pass post-fix) + the module suite |
| Behavior visible to users | One end-to-end probe (curl the endpoint, run the CLI command) in addition to tests |

Two costly mismatches to avoid: running the full 10-minute suite after a one-line rename
(wasteful — you'll start batching to avoid it), and running only a type-check after a logic
change (theater — types don't verify behavior).

## Step 2: Batching rules

1. **Logic changes: verify individually.** One behavioral edit per cycle.
2. **Mechanical changes may batch within one file** (a rename's call sites, formatting,
   import sorting) — then one check for the batch.
3. **Cross-file mechanical sweeps** (rename across 12 files): batch the sweep, but compile/
   type-check immediately after, before any behavioral work resumes.
4. If you notice three unverified edits stacked up, stop adding and verify now — you're
   already one edit past the limit.

## Step 3: Keep the feedback fast

1. At task start, establish the fast commands for THIS repo (from CI config or the manifest's
   scripts) and note them: the type-check command, the single-file test command, the full
   suite command.
2. If the tightest available check takes >~2 minutes, invest five minutes FIRST in finding a
   faster subset (single-file runner, `-k` filters, watch mode, `cargo check` vs full build).
   The investment pays back on every subsequent cycle — slow feedback is the root cause of
   batching, and batching is the root cause of entangled debugging.
3. Escalate breadth at boundaries: cheap check per edit → module suite per completed function
   → full suite at each unit checkpoint (and always before delivery — that final gate belongs
   to verification-and-review).

## Worked example

Task: add pagination to a list endpoint (handler + query + serializer + 2 call sites).

- Weak rhythm: edit all five places, run the suite once → 7 failures across 3 files, mixed
  causes, 40 minutes of untangling.
- Loop rhythm:
  1. Edit query function → run its unit test → green.
  2. Edit serializer → its test → red: cursor field name typo → fixed in 30 seconds (one
     suspect).
  3. Edit handler → module tests + `curl 'localhost:3000/orders?limit=2'` → green, response
     shape confirmed.
  4. Update 2 call sites (mechanical, batched) → `tsc --noEmit` → green.
  5. Checkpoint: full suite → green. Commit (if authorized).
  Same edits, zero entanglement; no failure ever had more than one suspect.

## Done when

Ongoing — the loop has no terminal state during implementation. You are following it when: no
behavioral edit was ever stacked on an unverified behavioral edit, the tree was never left red
while you moved on, and at every unit boundary the full relevant suite ran green. Hand off to
verification-and-review for the final pre-delivery gate.
