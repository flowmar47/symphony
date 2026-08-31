---
name: performance-optimization
description: Make code measurably faster or leaner without breaking it — define a target, measure a baseline, profile to find the ACTUAL bottleneck, apply optimizations in a fixed order of leverage, and re-verify correctness after each change. Trigger this when the user reports slowness, high latency, memory growth, or cost, sets a performance budget, or asks to "optimize" or "speed up" something. Do NOT trigger for functional bugs that happen to involve timing (use debugging-methodology) or for restructuring at equal performance (use safe-refactoring) — this skill exists to move a number.
---

# Performance Optimization

Optimization without measurement is guessing with extra steps. Intuition about bottlenecks is
wrong often enough that acting on it unmeasured wastes the time it was meant to save. The
number rules everything: define it, baseline it, move it, prove it.

## Step 1: Define the target and the workload

1. Pin the metric AND the goal: "p95 of `/search` under 300 ms at 50 rps", "import of the
   1M-row file under 2 min", "RSS under 512 MB". No target = no definition of done = optimization
   that never ends. If the user gave none, propose one and get a nod.
2. Pin the workload: realistic data at realistic scale. A query fast on 100 dev rows and slow
   on 10M production rows is the NORMAL case, not an edge case — measuring on toy data
   measures nothing.

## Step 2: Baseline before any change

Measure the current number, three runs (warm), record median and spread in your notes.
Every later claim of improvement is relative to this recorded baseline — "feels faster" is
not a result.

## Step 3: Profile — find where the time actually goes

Use the stack's profiler, not code reading:
- Rust: `cargo flamegraph` / `perf`; `--release` always — debug-build numbers are fiction.
- Node/TS: `node --prof` or `0x`/`clinic flame`; `console.time` brackets for coarse cuts.
- Python: `py-spy record` (no code change) or `cProfile` + `snakeviz`.
- SQL: `EXPLAIN (ANALYZE, BUFFERS)` on the real query with real data volume.
- Anything network-y: count the requests first — chattiness dominates before CPU does.

Read the profile for the top consumer. **Rule: no optimization is applied to code the profile
didn't indict.** If the profile surprises you (it usually does), that surprise just saved you
a week of optimizing the wrong thing.

## Step 4: Apply strategies in order of leverage

Try each level; only descend when the level above is exhausted for the indicted hotspot:

1. **Don't do the work:** cache repeated computation, dedupe repeated calls, early-exit,
   skip unused fields, paginate instead of load-all.
2. **Do the work fewer times / in bulk:** fix N+1 queries (join or batch), batch writes,
   buffer I/O, debounce, move loop-invariant work out of the loop.
3. **Do the work better:** right algorithm/data structure — dict lookup over list scan,
   sort-then-merge over nested loops, the missing database index.
4. **Tune the machinery:** connection pools, buffer sizes, compiler/runtime flags,
   `--release`.
5. **Parallelize:** only now — parallel versions of wasteful work multiply the waste and add
   race conditions to it.
6. **Micro-optimize:** last, rarely, and only with the profile still pointing there.

## Step 5: One change, two measurements

For EACH optimization: apply it alone → re-run the metric → re-run the correctness suite.
Keep a running table in your notes:

| Change | p95 before | p95 after | Tests |
|---|---|---|---|
| Add index on `orders(user_id, created_at)` | 1400 ms | 310 ms | green |
| Batch the price lookups | 310 ms | 180 ms | green |

A change that doesn't move the number gets REVERTED, even if it "should" help — dead
optimizations are complexity with no dividend. A change that breaks a test is a bug, not a
trade-off, unless the user explicitly accepts the trade.

## Step 6: Stop at the target

When the target from Step 1 is met: stop. Further optimization is scope creep with a
performance costume. Report the table, the final number vs. target, and any identified-but-
unneeded next levers ("materialized view would take it to ~80 ms if ever needed").

## Worked example

"The dashboard takes 8 s to load; get it under 2 s."

- Target: p95 page-data endpoint < 2 s on the staging dataset (4M rows). Baseline: 8.1 s.
- Profile (EXPLAIN + request log): intuition said "slow rendering"; reality: 41 sequential
  queries (N+1 on widgets) + one seq-scan aggregate. Rendering was 90 ms — untouched.
- Level 2: batch widget query → 41 calls → 2. 8.1 s → 2.9 s. Suite green.
- Level 3: index for the aggregate's filter → seq scan → index scan. 2.9 s → 1.3 s. Green.
- Target met — STOP. Cache layer (level 1) noted as unneeded next lever, not built.
- Report: table of both changes with numbers, final 1.3 s vs 2 s target, suite green.

## Done when

The target metric from Step 1 is met and demonstrated by recorded before/after measurements
on the realistic workload; every applied change is in the table with its own measured delta;
the full correctness suite is green after the final state; ineffective changes were reverted;
and no code the profiler didn't indict was "optimized".
