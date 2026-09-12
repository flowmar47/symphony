# SPEC — <lane name>: <one-line problem statement>

## GOAL
<One paragraph. What done looks like, in user-visible terms.>

## Writable scope
Only <repo/dir …> writable. Everything else read-only. (Parallel lanes: disjoint scopes.)

## Constraints
- <what must not change: versions, policy values, dependencies, public claims>
- No commits, pushes, or release/store actions — the conductor lands.
- You are not alone in the workspace. Preserve others' work; stop on overlapping ownership.

## Non-goals
- <the tempting adjacent work this lane must not do>

## STOP rule
If <premise> does not hold, STOP and report exactly what exists instead — do not scaffold.

## Acceptance criteria
- <observable required outcome and relevant edge cases>

## Evidence and budget
- <required check, or explicitly deferred validation with reason>
- <source and input identity, command, environment/pins, exit code and output path>
- <time/tool-call budget and exact remaining command if incomplete>
Reuse inspected unchanged evidence; return a compact verdict with artifact references,
not a full log dump. Mark all unperformed checks NOT RUN. Completion is not acceptance;
lower-model returns require frontier review by the conductor or an appropriate reviewer.
