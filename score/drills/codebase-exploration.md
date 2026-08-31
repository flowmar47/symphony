---
name: codebase-exploration
description: Map an unfamiliar repository before changing anything in it — structure sweep, entry points, configs, test baseline, targeted tracing, and mental-model confirmation. Trigger this the FIRST time you work in a repo (or an unfamiliar subsystem of a known repo) in a session, before your first edit there — whenever the user says "fix/add/change X" in code you have not yet mapped. Do NOT trigger for repos or areas you already mapped this session, for single-file scripts with no surrounding project, or for parsing the request itself (use task-planning) — this skill is about understanding the code, not the ask.
---

# Codebase Exploration

Understand before you touch. The cost of exploration is minutes; the cost of editing on a
wrong mental model is a broken subsystem discovered later and blamed on you.

## Step 1: Structure sweep (2 minutes)

1. List the repo root. Read `README` and the manifest (`package.json` / `Cargo.toml` /
   `pyproject.toml` / `go.mod`) — note language, package manager, and declared scripts.
2. Read the lockfile's top-level entries enough to know the major frameworks in play. The
   lockfile is ground truth for versions; your memory of the ecosystem is not.
3. Check `.github/workflows/` (or CI config). CI encodes the REAL build/test/lint commands —
   more reliably than the README, which drifts.

## Step 2: Find the entry points

Locate how the code actually starts: `main`/`index`/`app` files, the manifest's
`scripts`/`bin` entries, `Dockerfile` `CMD`, or the daemon/service definition. For a library,
locate the public surface (exports, `lib.rs`, `__init__.py`). You cannot place a change
correctly until you know what calls what from the top.

## Step 3: Map configuration and environment

Find `.env.example`, config files, and feature flags. Note which behavior is config-driven —
a "bug" is often a config difference, and an edit is sometimes the wrong fix for what a config
change does properly.

## Step 4: Establish the test baseline BEFORE the first edit

1. Find where tests live and what runs them (from CI, Step 1.3).
2. Run the suite — or the fastest relevant subset — before changing anything, and record the
   result in your notes.
3. **Rule:** a pre-existing failure discovered AFTER your edits will be attributed to you, and
   you'll waste time debugging code you didn't break. The baseline is your alibi and your
   safety net. If the suite can't run (missing env), record that fact instead.

## Step 5: Targeted exploration of the task area

1. Grep for the concrete anchors the task gives you: the route path, the error message text,
   the symbol name, the table name. Error strings are the highest-yield anchor — they're
   unique and land you at the exact site.
2. Trace ONE representative flow end-to-end (request → handler → service → storage, or
   input → parse → transform → output). One full vertical slice teaches more than reading
   four layers horizontally.
3. **Reading-depth rule:** read COMPLETELY any file you will edit; read the signatures and
   call sites of anything you will call; skim only what you merely pass through. Never edit a
   file you have not read in this session — no exceptions, however obvious the edit looks.
4. **Signature rule:** never assume an internal API's signature or behavior when you could
   verify it — grep for an existing call site (how it's used HERE beats how it's "usually"
   used) or read the definition. Two existing call sites that disagree with your assumption
   are a finding, not an inconvenience.

## Step 6: Confirm the mental model before the first edit

Make one falsifiable prediction and check it:
- "Hitting `/health` returns `{status: 'ok'}`" → curl it.
- "This function is only called from the scheduler" → grep proves 1 caller or reveals 3.
- "Deleting a user cascades to sessions" → find the FK or the test that encodes it.

If the prediction fails, your model is wrong — loop back to Step 5 before editing. If you
can't formulate any prediction, you haven't understood enough to edit.

## Worked example

Task: "Fix: CSV export drops the last row" in an unmapped Node repo.

1. Sweep: `package.json` → pnpm, vitest, express; CI runs `pnpm test && pnpm lint`.
2. Entry: `src/server.ts` mounts routes from `src/routes/`.
3. Baseline: `pnpm test` → 84 pass, 2 fail in `billing.test.ts` — recorded as PRE-EXISTING
   before any edit.
4. Anchor grep: "text/csv" → `src/routes/export.ts` → calls `serializeRows` in
   `src/lib/csv.ts`. Read both files fully.
5. Prediction: "`serializeRows` drops the final row when input lacks trailing newline
   handling" → 3-line REPL check with a 2-row array → confirmed (returns 1 data line).
6. Now — and only now — edit `csv.ts`, add the regression test, re-run: 85 pass, same 2
   pre-existing failures.

## Done when

You can state without hedging: where the change goes, what calls it and what it calls, the
exact command that verifies it, and the recorded baseline test result — and every file you're
about to edit has been read in full this session.
