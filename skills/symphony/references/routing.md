# Live routing

Load when choosing a model or effort. IDs below are **shapes**, not names to reuse.
Take every concrete identifier from this session's host catalog.

## Discovery surfaces

Use the first surface that exists. Stop if it fails; do not invent a fallback ID.

| Host | Where the live list is | How effort is selected |
|---|---|---|
| Native subagent/Task tool | The tool schema's current model list for this session | Effort/thinking suffix on the slug, or a separate effort field if the host has one |
| Codex CLI | `python3 scripts/symphony-models.py` (`model/list` only) | `supportedReasoningEfforts` / `--effort` / `auto` → advertised default |
| User/env pin | Explicit ID in the request or `SYMPHONY_*_MODEL` | Must still be in the live catalog |

Do not read private model caches. Do not construct a successor (`vN+1`, "latest",
unlisted aliases). If the catalog is empty or the tool omits a model parameter, stay
on the conductor or stay solo.

Symphony invocation authorizes internal model/effort selection. The ID passed to the
host must still be one the host listed **this session**.

## Map the catalog to bands

Classify **listed options**, not vendors. Use host signals in this order:

1. User pin or an accepted task-class route in records.
2. Host labels/descriptions: speed, cost, default, reasoning, frontier — descriptions
   are routing signals, not a security boundary.
3. Structural tokens in the listed ID, case-insensitive: `fast`, `flash`, `mini`,
   `nano`, `lite` → Fast; presence of high/max/xhigh thinking **as a supported
   effort on that family** means the family can fill Frontier.
4. Host default → Standard when no better signal exists.
5. Strongest remaining reasoning controls (highest supported non-delegating effort,
   latest version of that family) → Frontier.

Group by family (the prefix before a version). When the user did not pin a version,
keep only the newest version the catalog lists for that family. Treat
effort/thinking suffixes as **effort**, not as a different model.

If two families can fill Frontier, prefer: user pin → proven route → host default
among them → any. A newer listed version of the same family displaces the older one
without a Symphony edit.

Unknown capability: the option may still run, but its return is treated as
non-frontier until a frontier review completes.

Never infer nested-delegation, premium tiers, or extra-agent modes from a larger
effort ordinal or from a name. Those require explicit compatible authorization.

## Work class → band and effort

| Work class | Band | Effort | Stay solo / go frontier immediately when |
|---|---|---|---|
| Grep, extract, format, rename, bounded file recon | Fast | Low, or the host's cheap thinking suffix | The raw content must stay in the conductor's context anyway |
| Spec-bound implement, tests, integration of known patterns | Standard | Medium / high | Spec is missing, requirements interact, or the last cheap attempt failed on capability |
| Architecture, ambiguous ask, security, data integrity, hard debug | Frontier | High | Interacting constraints, auth/privacy, or irreversible blast radius → max if the host has a non-delegating max |
| Review of another model's artifact | Frontier | Match the slice: medium deterministic, high behavioral, max interacting/security | Reviewer would be the author, or no frontier option exists → pending |

`auto` / default effort is allowed only when it is **not** a delegating mode. An
auto-selected nested-delegation effort is refused; an explicit one needs attested
authority and a compatible concurrency/time budget.

**Inherit** (omit the model argument) only when the conductor's own model and effort
already match the row above. Otherwise pass an explicit catalog ID.

## Dispatch record

Before launch, write one line the conductor can reuse:

```
slice: <name>
work: <retrieval | mechanical | spec-bound | architecture | review>
band: <fast | standard | frontier>
id: <exact catalog id>
effort: <exact host value>
reviewer: <frontier id + effort, or conductor-pass, or pending>
why: <one sentence>
```

Native launch: one subagent call per independent slice, **same turn** for parallelism.
Each prompt is a complete spec (goal, acceptance, scope, constraints, non-goals,
inputs, stop rule, evidence budget). CLI launch: [cli.md](cli.md).

## Quality-equivalence protocol

The accepted artifact must pass the checks a frontier-max solo pass would. Cheaper
execution is allowed only with this sequence:

1. **Specify** at frontier quality. A Fast/Standard builder without acceptance
   criteria is refused, not attempted.
2. **Run** the cheapest band that can follow that spec. Independent slices in
   parallel; shared files serialized.
3. **Prove** with source-bound evidence. Completion ≠ acceptance.
4. **Review** on current frontier, artifact-only, effort as in the table.
5. **Repair once** if the miss is local; **escalate the slice** if the miss is
   capability (dropped constraint, wrong frame, cannot hold interactions). Do not
   escalate auth/env/tool failures.

A Fast lane that a frontier reviewer then rewrites is a loss versus starting on
frontier. Count review, repair, and integration in the comparison.

Do not:

- Skip review to save tokens.
- Ritual-cheap a problem that was frontier from the first sentence.
- Claim savings without host counters through acceptance.
- Treat host default, a remembered name, or "it completed" as frontier.

## Common mistakes

| Mistake | Correction |
|---|---|
| Reusing last month's family names from this file | Read this session's catalog |
| Inheriting frontier onto a scout | Fast band, explicit cheap ID |
| Inheriting a cheap conductor onto review | Frontier reviewer, or pending |
| Inventing a slug or successor ID | Only listed IDs |
| Cheap retries on a hard kernel | Frontier immediately |
| Nested/premium effort by default | Explicit authority + budget |
| Author marks its own work accepted | Separate frontier review |
| Speaking kebab slugs to the user | Use the user's naming scheme |
