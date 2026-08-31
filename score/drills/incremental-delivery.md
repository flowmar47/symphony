---
name: incremental-delivery
description: Build large multi-part deliverables — multi-file projects, migrations, long documents, N-of-the-same-thing work — in verified increments with dependency ordering, checkpoints, a running state note, and consistency sweeps. Trigger this when a task will produce 3+ files, spans more sub-deliverables than fit in one pass, involves repeating a pattern across many sites (endpoints, parsers, pages, records), or is explicitly requested to be done incrementally or resumably. Do NOT trigger for single-file changes (implementation-standards suffices) or for the initial breakdown of an ambiguous request (use task-planning first — this skill governs execution after the plan exists).
---

# Incremental Delivery

Never "write everything, then test everything" — that strategy converts N independent small
bugs into one entangled debugging session at the end. Small verified steps beat large
unverified strides even when the stride looks 20% faster; something always goes wrong.

## Step 1: Order the units

1. **Dependency order:** shared types/schemas → pure logic → I/O adapters → interfaces
   (API/CLI/UI) → integration glue. Consumers are written after the things they consume exist
   and are verified.
2. **Risk first within that order:** the unfamiliar API, the format never parsed, the
   algorithm you're unsure of — prove it in isolation before the plan depends on it. If it
   fails, the plan changes while changing is cheap.
3. **Pattern before replication:** building N similar things? Build ONE end-to-end, verify it,
   THEN replicate. A flaw in the pattern costs 1× to fix before replication and N× after.

## Step 2: Checkpoint after every unit

1. After each coherent unit, run the fastest available check: compile, import, unit test, or a
   smoke run. Never stack a second untested layer on a first.
2. In a git repo, commit (or otherwise mark) each known-good point so revert has a target.
3. If a unit balloons mid-way: split it, checkpoint the finished half. Do not power through to
   a distant checkpoint.

## Step 3: Maintain the state note

On any task long enough to survive a session break (or that another model might resume), keep
a running note — a scratch file or persistent todo — containing:

- Units done / units remaining (the ordered list, checked off).
- **Decisions later units must honor:** naming scheme, error envelope shape, ID types, field
  formats — recorded the moment they're made.
- Open questions and assumptions so far.
- The exact next action, written for a cold reader.

Consult the note BEFORE starting each new unit — your memory of a decision made 8 units ago
has drifted; the note hasn't. Write it as if a different, colder model will resume from it,
because one might.

## Step 4: Propagate interface changes immediately

When unit 7 forces a change to unit 2's interface (renamed field, new parameter, changed
return shape):

1. Grep for EVERY consumer of the old interface — do not fix only the ones you remember.
2. Propagate the change to all of them NOW, not "after finishing unit 7".
3. Re-run the earlier units' checks. Deferred propagation is how half-renamed codebases happen.

## Step 5: Final consistency sweep

After the last unit, one deliberate pass over the WHOLE deliverable:

- Same naming conventions from first file to last? (Early files follow the original plan;
  late files follow how the plan evolved — reconcile them.)
- Same error format / response envelope / logging shape everywhere?
- Do early sections still accurately describe what later sections actually do? Documents
  drift exactly like code.
- Re-read the ORIGINAL request one final time and check every stated requirement and process
  instruction against the finished whole — long tasks decay instructions silently.

## Checklist per unit

- [ ] Consulted the state note before starting?
- [ ] Unit's own check run and passing?
- [ ] Any new cross-cutting decision recorded in the note?
- [ ] Any interface change propagated to ALL existing consumers and their checks re-run?
- [ ] State note updated (done list, next action)?

## Worked example

Task: build a CLI tool with 5 subcommands reading a config, calling an API, and writing
reports.

- Order: (1) config loader + types [everything consumes it], (2) API client for ONE endpoint —
  riskiest, unfamiliar API — proven with a live smoke call, (3) first subcommand end-to-end
  [the pattern], (4–6) remaining subcommands [replication], (7) shared `--help`/error polish.
- Checkpoint: after unit 2, the smoke call reveals the API paginates — recorded in the note:
  "all list endpoints must paginate; client returns iterators, not lists." Units 3–6 honor it;
  without the note, subcommand 5 (written hours later) would have returned truncated lists.
- Unit 4 renames a config field for clarity → grep finds 3 consumers (units 1, 3, and a test);
  all updated in the same edit session; unit-1 and unit-3 tests re-run green.
- Sweep: subcommands 3 and 6 formatted errors differently (evolved mid-task) — reconciled;
  original request re-read; requirement "machine-readable `--json` output" found present in
  units 3–5 but missing in 6 — fixed before delivery instead of shipped missing.

## Done when

Every unit has passed its own check at its own checkpoint; all interface changes were
propagated the moment they happened; the final consistency sweep is complete; the finished
whole has been re-checked against the original request line by line; and the state note's
"remaining" list is empty or every leftover item is explicitly reported as deferred.
