# Task Briefing Template

For the human. This is how to phrase a task for a less-capable model so its weaknesses are
pre-compensated by your framing. The model's failure modes are predictable — skipped steps,
unexamined assumptions, silently-dropped requirements, happy-path-only code, confident guessing
about version-sensitive facts. Each section below pre-empts one of them. Fill in what applies;
omit what doesn't. Two minutes of briefing saves an hour of correction.

---

## The template

```
GOAL
<One or two sentences: what should be true when this is done. State the outcome,
not the activity. "Users can reset their password via email" — not "work on auth".>

CONTEXT
<Where the work happens: repo/paths, the stack and pinned versions, and the 2–3
files or functions most relevant. Point the model at them so it doesn't guess.
Include anything non-obvious it cannot infer from the code.>

CONSTRAINTS (hard — do not violate)
- <e.g. no new dependencies>
- <e.g. don't touch the database schema>
- <e.g. must stay backward-compatible with the existing API>
- <e.g. work incrementally / commit as you go / don't commit>

ACCEPTANCE CRITERIA (how we'll both know it's done)
- <a concrete, checkable condition — "`pytest tests/auth/` passes">
- <"POST /reset with a bad token returns 401, not 500">
- <"handles the empty-input and duplicate-request cases">

SCOPE
In scope: <the specific things to build>
Out of scope: <things NOT to build — name them, or the model may gold-plate>
If you hit something ambiguous: <"ask me" for expensive/irreversible; "pick the
conventional option and note it" for cheap/reversible>

VERIFICATION
<The exact commands to run: build, test, lint. If the model can't run something
(no DB, no creds), say so and say what to do instead.>

SIZE / CHUNKING
<If large: break it here, or tell the model to plan and checkpoint. e.g. "do the
data layer first, show me, then continue" — smaller chunks fail less.>
```

---

## Guidance per section — why each matters

**GOAL — state the end state, not the task.** "Fix the export" invites the model to fix the
first plausible cause. "The CSV export currently drops the last row; it should include all
rows" gives it a verifiable target and a symptom to reproduce.

**CONTEXT — point, don't make it hunt.** A weaker model wastes budget (and makes wrong guesses)
searching an unfamiliar repo. Naming the relevant files and the pinned versions removes the two
biggest sources of error: wrong location and wrong-version API assumptions. Always include
version-pinned facts — the model's training memory of a library may be stale.

**CONSTRAINTS — make prohibitions explicit and up front.** The model weighs the deliverable
heavily and can forget an unstated "don't". Anything that must NOT change belongs here in
plain terms. Process instructions ("one file at a time", "don't commit") are constraints too —
list them, they carry the same weight as functional ones.

**ACCEPTANCE CRITERIA — give it the test it will be graded by.** This is the highest-leverage
section. Concrete, checkable criteria convert "I think it's done" into "it demonstrably meets
these", and they double as the model's own verification checklist. Include the unhappy paths
you care about (error cases, edge cases) — otherwise you'll get happy-path-only code.

**SCOPE — name the out-of-scope explicitly.** Left unsaid, a weaker model fills perceived gaps
with speculative abstractions and features you didn't ask for. "Out of scope: multi-provider
support, config UI" prevents the gold-plating directly. Also state the ambiguity rule so the
model knows when to ask vs. proceed — this prevents both the blocking-question spam and the
silent-wrong-assumption failure.

**VERIFICATION — hand over the commands.** The model must verify with real execution, not
assertion. Give it the exact commands so "tests pass" is a run, not a hope. If verification
isn't possible in its environment, say so — otherwise it may claim success it can't back.

**SIZE / CHUNKING — pre-split large work.** Coherence degrades over long tasks. For anything
big, either break it into stages yourself or instruct "plan first, checkpoint after each
stage, show me before continuing". Smaller verified chunks beat one large unverified push.

---

## Worked example — weak brief vs. strong brief

**Weak:** "Add rate limiting to the API."
(No target number, no scope, no criteria — you'll get some algorithm, applied somewhere,
possibly a new dependency, tested on nothing, maybe per-node when you needed global.)

**Strong:**
```
GOAL   Authenticated users are limited to 100 requests/minute per user across all API
       endpoints; over-limit requests get HTTP 429 with a Retry-After header.
CONTEXT  Node/Express app in src/api/. Existing middleware in src/api/middleware/.
         Redis is already available (src/lib/redis.ts) — we run 4 instances, so the limit
         must be shared across them. redis client v4.
CONSTRAINTS  No new rate-limit dependency if Redis INCR suffices. Don't change existing
             route handlers' signatures.
ACCEPTANCE  - 101st request within a minute from one user → 429 + Retry-After.
            - Limit holds across instances (test against 2 processes), not per-process.
            - Unauthenticated routes unaffected.
            - Tests in src/api/middleware/rateLimit.test.ts pass.
SCOPE  In: the middleware + wiring + tests. Out: per-endpoint custom limits, an admin
       override UI, IP-based limiting.
       Ambiguity: cheap/reversible → pick conventional + note it; anything touching the
       Redis key schema → ask me first.
VERIFICATION  pnpm test src/api/middleware; pnpm lint. Manual: hit /orders 101× with one token.
SIZE  One sitting; no chunking needed.
```

## Done when (for the human)

Your brief states an outcome-shaped goal, points at the relevant files and pinned versions,
lists hard constraints and out-of-scope items explicitly, gives concrete acceptance criteria
that include the unhappy paths, and hands over the verification commands. If all five are
present, you've pre-compensated for the model's main weaknesses.
