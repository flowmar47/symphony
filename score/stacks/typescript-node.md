# Stack Standards — TypeScript / Node

Concrete standards for TypeScript on Node (services, dashboards, CLIs) and browser/React
frontends. Applies on top of PLAYBOOK.md and the skills. Existing repo conventions win over
this file.

## Project structure

- Feature/domain folders (`orders/`, `agents/`, `incidents/`), each with its own
  routes/handlers, service logic, and types co-located — not global `controllers/`,
  `services/`, `models/` layer folders.
- One responsibility per file, ~200–400 lines. Barrel `index.ts` files only at package
  boundaries, not every folder (they wreck tree-shaking and create import cycles).
- Keep I/O at the edges: HTTP handlers and DB access thin; pure logic in separate functions
  that take data and return data, testable without a server or database.

## TypeScript configuration and typing

- `strict: true`, always. Also `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` on
  new projects — they catch the bugs `strict` alone misses.
- **`any` is banned.** When you don't know a type, use `unknown` and narrow. External JSON is
  `unknown` until validated (see below). Escape hatches (`as`, `!`, `@ts-ignore`) carry a
  comment naming the forcing constraint; `@ts-expect-error` over `@ts-ignore` so it fails when
  the underlying issue is fixed.
- Model illegal states out: discriminated unions (`{ status: 'ok', data } | { status: 'err',
  error }`) over structs of optional fields. `type` for unions/aliases, `interface` for object
  shapes that may be extended/implemented.
- Validate external input with a schema library (zod is the default here): parse at the
  boundary, infer the static type from the schema (`z.infer`) so runtime and compile-time
  agree. Never cast untrusted JSON with `as`.

## Async and error handling

- `async/await` only — no raw `.then()` chains, no callback-style APIs left un-promisified.
- **Never leave a promise floating.** Every async call is `await`ed or explicitly handled;
  enable `no-floating-promises`. Unhandled rejections crash Node or vanish silently.
- `Promise.all` for independent concurrent work; a sequential `await` loop only when each
  iteration depends on the last. `Promise.allSettled` when partial failure is acceptable.
- Errors: `throw` `Error` subclasses with context, never strings. Catch narrowly at the layer
  that can act; centralize HTTP error → response mapping in one middleware, not scattered
  try/catch that leak stack traces to clients.
- Node built-ins: prefer them (`fs/promises`, `crypto.randomUUID()`, `URL`, `fetch`) over
  adding `uuid`, `node-fetch`, `axios` when the built-in suffices.

## Testing and coverage

- Test runner per repo (vitest or jest — check the manifest). Tests co-located as `*.test.ts`
  or in `__tests__`.
- Every behavior gets a test asserting a concrete value; `expect(x).toBeDefined()` /
  `.not.toThrow()` as the sole assertion is not a test. Bug fixes get a failing-first
  regression test.
- Mock at the boundary (the HTTP client, the DB module), not deep internals. Prefer injecting
  the dependency over `jest.mock` module magic where practical.
- Frontend: React Testing Library — assert on what the user sees/does (roles, text,
  interactions), never on component internal state or implementation detail.
- Coverage ~80% of logic; integration tests for API endpoints exercising real status codes
  (200 AND 400/401/403/404/500), not just the happy path.

## Preferred libraries / adding a dependency

- Validation: zod. HTTP server: whatever the repo uses (Express/Fastify) — don't introduce a
  second. Dates: `date-fns` or `Temporal` where available — never hand-roll timezone math.
  IDs: `crypto.randomUUID()`. DB: the repo's existing client/ORM.
- Criteria to add: not already covered by stdlib or an installed dep; maintained; typed
  (ships `.d.ts` or has `@types`); sane transitive footprint (`npm ls` before committing);
  license fits. One dependency per problem; never a framework for one function.
- Lockfile committed; `npm audit` / `pnpm audit` in the verification loop. Use the repo's
  package manager (pnpm here) — don't mix.

## Verification commands (this stack)

`tsc --noEmit` (fast type-check, per-edit) → single-file test run (per unit) → full test +
`eslint` + `prettier --check` before delivery. ESLint errors are fixed, not `// eslint-
disable`d without a justifying comment.

## Anti-patterns → corrections

- **`any` to move past a type error** → `unknown` + narrowing, or fix the actual type. `any`
  disables checking for everything downstream of it.
- **`useEffect` for derived state / data fetching in React** → derive during render for
  computed values; use the data-fetching library the app already has (React Query/SWR) or a
  server component. Effects are for synchronizing with external systems, not everything.
- **Floating promise / forgotten `await`** (`db.save(x)` with no await) → the write may not
  finish before the response; always await or explicitly handle.
- **`==` / truthiness checks that conflate `0`/`''`/`null`/`undefined`** → `===`, and check
  the specific case (`x == null` is the one sanctioned loose check, for null-or-undefined).
- **Barrel-file import cycles** → import from the specific module; reserve barrels for public
  package edges.
- **Leaking internals to the client** (raw error/stack in the HTTP response) → generic message
  out, detail to server logs (also an integrity/security rule).
- **`process.env.X` scattered through the code** → validate all env once at startup (zod
  schema), export a typed config object; fail fast if a required var is missing.
