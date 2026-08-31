---
name: dependency-changes
description: Add, upgrade, or migrate third-party dependencies safely — read the changelog for the exact version jump, isolate the change, run full verification, and keep rollback ready. Trigger this when the task involves bumping a package version, adding a new dependency, replacing one library with another, resolving a dependency vulnerability, or a lockfile update. Do NOT trigger for using an already-installed dependency in application code (that's normal implementation), or for deciding WHETHER a new dependency is warranted (use architecture-decisions' dependency sub-decision) — this skill is about executing the change without breakage.
---

# Dependency Changes

A dependency change is a change to code you didn't write and didn't review, arriving with its
own bugs and behavior shifts. Treat every bump as a code change requiring verification, never
as routine housekeeping.

## Step 1: Know exactly what version moves where

1. Read the lockfile for the CURRENT installed version — not the manifest range, the actual
   resolved version. That's your "from".
2. Determine the "to" and classify the jump by semver: patch (x.y.Z), minor (x.Y.z), or major
   (X.y.z). Major jumps carry breaking changes by definition — budget accordingly.
3. Note transitive impact: does this bump drag peer/transitive dependencies with it? `npm ls
   <pkg>` / `cargo tree -i` / `pip show` reveals who else is affected.

## Step 2: Read the changelog for the SPECIFIC range

1. Read the CHANGELOG / release notes for every version between from and to — not just the
   target. Bugs and breaking changes accumulate across the intermediate releases you're
   skipping.
2. For a major jump, find the migration guide. Search the notes for "BREAKING", "removed",
   "deprecated", "renamed". List each breaking item that touches an API your code actually
   uses (grep your code for the symbols).
3. This is version-sensitive external knowledge — do not rely on training memory of the
   library's API (see the research-and-verification skill). Read the notes for the real
   versions, fetched this session.

## Step 3: Isolate the change

1. One dependency change per commit/branch. Never bundle a version bump with feature work —
   when something breaks, you must know whether it was the bump or your code, and a mixed diff
   destroys that signal.
2. If bumping several dependencies, do them one at a time with a full verification between
   each. A batch bump that fails gives you N suspects; sequential bumps give you one.
3. Record the pre-change lockfile state (it's your rollback target — commit it or copy it).

## Step 4: Apply and adapt

1. Update the manifest, regenerate the lockfile with the project's tool (`npm install`,
   `cargo update -p`, `uv lock` / `pip-compile`) — never hand-edit a lockfile.
2. Address each breaking item found in Step 2: update call sites for renamed/removed APIs,
   migrate deprecated usage. Grep to find every site; don't fix only the ones you remember.
3. If the new version needs a config or peer-dependency change, do it in the same commit.

## Step 5: Full verification (broader than usual)

A dependency touches code paths your unit tests may not cover directly. Escalate breadth:
1. Reinstall from the lockfile clean (`rm -rf node_modules && npm ci`, fresh venv) — confirm
   it resolves and installs reproducibly, not just on your incremental state.
2. Build + full test suite + lint + type-check. Type errors after a bump often ARE the
   breaking changes surfacing — read them, don't suppress them.
3. Run the app / a smoke path — some breakages (behavioral, not type-level) only appear at
   runtime.
4. Re-run the security audit (`npm audit` etc.) — confirm a security-motivated bump actually
   cleared the advisory, and didn't introduce a new one.

## Step 6: Rollback readiness

If verification fails and the fix isn't quick: revert to the recorded lockfile state (Step 3),
confirm green is restored, and report — "bump X 2.x→3.x blocked: it removes `Y` which the auth
module depends on; needs migrating `Y`→`Z` first (est. N sites). Staying on 2.x meanwhile."
A clean revert plus a clear blocker report beats a half-migrated broken tree.

## Worked example

Task: "Upgrade `axios` to fix the CVE."

1. Lockfile: current `0.27.2`. Target: latest `1.x` clearing the advisory → `1.7.x`. Major jump.
2. Changelog 0.27→1.0: BREAKING — default export/interceptor changes, `axios.get` error shape
   changed. Grep code: 14 call sites, 2 use the changed error shape.
3. Isolated branch `chore/axios-1.x`; lockfile copied as rollback target.
4. `npm install axios@^1.7`; update the 2 error-handling sites; grep confirms the other 12 are
   compatible.
5. `npm ci` clean → build → full suite → RED: one test asserted the old `error.response`
   path; it's testing real behavior that changed → update the assertion (legitimate — the
   contract changed), NOT silenced. Green. Smoke: live request works. `npm audit` → advisory
   cleared, none introduced.
6. Commit alone: `chore: upgrade axios 0.27→1.7 (fixes CVE-XXXX; migrate error handling)`.

## Done when

The exact version range's changelog was read and every breaking item touching your code
addressed; the change is isolated to its own commit; a clean reinstall + full build/test/lint/
smoke passes; a security-motivated bump is confirmed to clear the advisory; and the rollback
target is recorded so a failed bump can be cleanly reverted with a blocker report.
