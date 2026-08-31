---
name: git-discipline
description: Rules for commits, branches, diffs, and history when working in a git repository — checkpoint strategy, pre-commit diff review, message format, and the hard prohibitions on destructive operations. Trigger this whenever work happens in a git repo and involves staging, committing, branching, or any history-affecting command; before EVERY commit; and the moment you are tempted to run force-push, reset --hard, clean -fd, rebase, or amend. Do NOT trigger for the edit-test cycle itself (use verification-loop) or for reviewing code quality of a diff (use code-review) — this skill governs version-control mechanics and safety only.
---

# Git Discipline

Git is the safety net and the audit trail. Used carelessly it becomes the accident: history
rewritten, work destroyed, secrets published. The rules below are ordered: prohibitions first
because they are absolute; craft second.

## Hard prohibitions (no exceptions without explicit user instruction)

1. **Never commit or push unless the user asked or their workflow clearly expects it.** On a
   long task, ask ONCE at the start: "checkpoint-commit as I go, or leave everything unstaged?"
   If no commits are authorized, checkpoint with `git stash push -m "checkpoint: <state>"` or
   record known-good SHAs in your notes instead.
2. **No force pushes. No history rewrites of anything pushed** (`rebase`, `commit --amend`,
   `filter-branch` on published commits). To undo a pushed commit, use `git revert` — it
   preserves history.
3. **No destructive working-tree operations without explicit confirmation in THIS
   conversation:** `reset --hard`, `checkout -- .` over uncommitted work you didn't create,
   `clean -fd`, branch deletion with unmerged work. Before asking, run `git status` and
   `git stash list` and report what would be lost.
4. **Never commit on the default branch.** Branch first: `git checkout -b
   <type>/<short-slug>` (e.g. `fix/csv-last-row`).
5. **No secrets, ever.** Before every commit, scan the staged diff for keys, tokens,
   passwords, connection strings, and `.env` content. One match = unstage, move to env/secret
   manager, and check whether the value was ever committed before (if yes, tell the user it
   needs rotation — removal from HEAD does not un-leak it).
6. **No generated junk:** build artifacts, `node_modules`/`target`/`__pycache__`, editor
   files, your own WORKING_NOTES.md. If it's generated and not ignored, fix `.gitignore` in
   the same commit rather than committing the junk.

## Commit craft

1. **Small and coherent:** one logical change per commit — a commit you can describe in one
   sentence without "and also". Mechanical rename and behavior change are two commits, so the
   reviewer can skim one and scrutinize the other.
2. **Stage by path, never blind:** `git add src/lib/csv.ts tests/csv.test.ts` — never
   `git add .` or `git add -A`, which are how junk, secrets, and unrelated edits get in.
3. **Review the FULL staged diff before every commit:** `git diff --staged`, read every hunk.
   You are looking for: leftover debug prints, unrelated drive-by edits, secrets, and hunks
   you can't explain. Any of those = fix before committing. This review is mandatory even
   when "sure" — especially when sure.
4. **Message format:** imperative summary ≤72 chars stating the change
   (`fix: include final row in CSV export`); body only when the WHY isn't obvious from the
   diff — the constraint, the bug mechanism, the rejected alternative. Never narrate the
   process ("tried X then Y").
5. **Checkpoint rhythm (when commits are authorized):** commit at every verified-green unit
   boundary (see verification-loop). Never commit a known-red state; if you must save a red
   work-in-progress, use a stash with a descriptive message instead.

## Recovery habits

- Before any risky operation you WERE authorized to run, note the current SHA
  (`git rev-parse HEAD`) in your working notes — that's the rollback target.
- Prefer additive recovery (`revert`, new commit) over subtractive (`reset`) whenever the
  branch may have been seen by anyone else.
- `git reflog` is the last-resort undo — remember it exists before declaring work lost.

## Worked example

Task: fix a bug; user said "commit as you go" at session start.

1. `git checkout -b fix/csv-last-row` (never on `main`).
2. Fix + regression test; `pnpm test` green.
3. `git add src/lib/csv.ts tests/csv.test.ts` (by path).
4. `git diff --staged` — review finds a `console.log(rows)` left in. Remove, re-stage, re-test.
5. Commit: `fix: include final row in CSV export when trailing newline absent`.
6. Later, a second improvement to error messages in the same file → separate commit, not
   squashed in.
7. Push only because the user asked for a PR; `git push -u origin fix/csv-last-row` — no
   force flags.

## Done when

Every commit on the branch is one sentence-sized logical change whose full staged diff you
read before committing; nothing was committed to the default branch, force-pushed, or
history-rewritten; no secret or generated file is in any commit; and every destructive
operation that ran had explicit user confirmation from this conversation.
