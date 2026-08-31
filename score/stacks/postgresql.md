# Stack Standards — PostgreSQL / Supabase

Concrete standards for schema, queries, migrations, and access (Postgres directly, and via
Supabase/PostgREST on Cloud Run). Applies on top of PLAYBOOK.md and the skills. Existing repo
conventions win over this file.

## Schema design

- `snake_case` everywhere; tables plural (`orders`), columns singular (`created_at`). Primary
  keys: `id` as `bigint generated always as identity`, or `uuid`/ULID when IDs must be
  client-generated or non-enumerable. Never expose a sequential PK where enumeration is a leak.
- Every table has `created_at timestamptz not null default now()`; add `updated_at timestamptz`
  (maintained by trigger) where rows mutate. **`timestamptz` always, never `timestamp`** —
  naive timestamps are a timezone bug in waiting. Store UTC.
- Normalize to 3NF by default; denormalize only with a measured read reason, and document it.
  Money as `numeric`, never `float`. Constrained sets as an `enum` type or a `check`, or a
  lookup table when the set changes at runtime.
- Constraints are the source of truth, in the database, not only in app code: `not null`,
  `unique`, `foreign key` with an explicit `on delete` action (`cascade`/`restrict`/`set null`
  — chosen deliberately), and `check` for domain rules. The app enforcing an invariant the
  schema doesn't is an invariant that will be violated.

## Indexing

- Index every foreign key (Postgres does NOT do this automatically) and every column in a
  frequent `WHERE`/`JOIN`/`ORDER BY`.
- Composite index column order = equality columns first, then range/sort. Match the index to
  the query's actual predicates.
- Partial indexes for queries over a subset (`where deleted_at is null`); GIN for `jsonb`/
  full-text/array membership. Don't over-index write-heavy tables — every index taxes writes.
- Validate with `EXPLAIN (ANALYZE, BUFFERS)` on realistic data volume — a "seq scan" on a
  large table where you expected an index scan is the finding.

## Queries

- **Parameterized/bound queries only.** No string interpolation of values into SQL, ever —
  SEC-CRITICAL otherwise, no exceptions for "internal" queries.
- Kill N+1: one query with a `join` or `where id = any($1)` over N per-row queries. This is
  the single most common performance defect in app-driven Postgres.
- Select the columns you need, not `select *` in application code (it breaks silently when the
  schema grows and ships unused data). `*` is fine in ad-hoc exploration.
- Keep transactions short; know the isolation level; guard concurrent read-modify-write with
  the right lock or `insert ... on conflict` rather than check-then-insert races.
- Set-based operations over row-by-row loops in the app; let the database do the join/aggregate.

## Migrations

- Every schema change is a migration file, ordered, committed, applied through the project's
  tool (Supabase migrations / the repo's migration runner) — never a manual `ALTER` on a live
  DB, and never hand-edit an already-applied migration.
- Migrations are forward-only in production but must be reviewed as reversible in intent: know
  the down/rollback path before applying. Test the migration on a copy with representative data
  before production.
- **Expand/contract for anything with live traffic:** add the new column/table (nullable or
  defaulted) → backfill in batches → switch the app → drop the old in a later migration. Never
  a single migration that renames/drops a column the running app still reads.
- Backfills on large tables run batched, not one statement that locks the table for minutes.

## Supabase / PostgREST specifics

- **Row Level Security is not optional.** Any table reachable through PostgREST/the anon or
  authenticated role has `enable row level security` plus explicit policies. A table exposed
  without RLS is a full data leak — verify RLS is ON, don't assume it.
- Write least-privilege policies per role (`anon`, `authenticated`, `service_role`); never lean
  on `service_role` from client-reachable code. Test policies from the intended role, including
  the negative case (role that must NOT see the row returns nothing).
- Prefer database constraints + RLS + views over pushing all logic to the edge/app — but keep
  business logic the app owns in the app; use `security definer` functions sparingly and audit
  each (they bypass RLS by design).
- Connection management on Cloud Run: use the pooler (pgBouncer/Supabase pooler) — serverless
  scale-out exhausts direct connections fast.

## Verification (this stack)

Run migrations against a scratch/branch database → `EXPLAIN (ANALYZE, BUFFERS)` on new/changed
queries at realistic volume → test RLS policies from each role (positive and negative) →
confirm constraints reject the bad rows they're meant to. Never verify only against 100 dev
rows — scale hides here.

## Anti-patterns → corrections

- **App-side uniqueness/FK checks without the DB constraint** → add the constraint; the app
  check races and eventually admits a dupe.
- **`text` for everything** → use the real type (`timestamptz`, `numeric`, `boolean`,
  `jsonb`, `enum`) so the DB validates and indexes properly.
- **Unindexed foreign key** → index it; joins and cascade deletes seq-scan without it.
- **`select *` feeding an ORM in a hot path** → name columns; avoid over-fetch and
  schema-growth breakage.
- **Storing JSON blobs for queryable structured data** → columns + constraints; reserve
  `jsonb` for genuinely schemaless/variable payloads, and GIN-index it if queried.
- **Table exposed via PostgREST with RLS off** → enable RLS and add policies before it ships.
- **Single migration that drops/renames a live column** → expand/contract across migrations.
- **Naive `timestamp` columns** → `timestamptz`, UTC.
