# SPEC — <lane name>: <one-line problem statement>

## GOAL
<One paragraph. What done looks like, in user-visible terms.>

## Writable scope
Only <repo/dir …> writable. Everything else read-only. (Parallel lanes: disjoint scopes.)

## Constraints
- <what must not change: versions, policy values, dependencies, public claims>
- No commits, pushes, or release/store actions — the conductor lands.

## Non-goals
- <the tempting adjacent work this lane must not do>

## STOP rule
If <premise> does not hold, STOP and report exactly what exists instead — do not scaffold.

## Proof
Run and include verbatim:
- <build command>
- <test command with totals>
