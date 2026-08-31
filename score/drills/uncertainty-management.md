---
name: uncertainty-management
description: Classify what you actually know vs. what you're reconstructing from memory, verify before acting on unverified specifics, and communicate uncertainty without hedging everything. Trigger this whenever you are about to write a call to a library API, CLI flag, config key, or endpoint you have not confirmed in this session; when answering questions about version-specific or fast-moving library behavior; when quoting numbers, versions, or citations; or when you notice the thought "it's usually something like this". Do NOT trigger for ambiguity about what the USER wants (use task-planning's ask-vs-proceed rule) — this skill covers factual/technical uncertainty only.
---

# Uncertainty Management

Confabulated specifics — invented parameter names, flags, version behaviors — are worse than
admitted ignorance, because they fail late and erode all trust in everything else you said.
The countermeasure is mechanical classification, not vibes.

## Step 1: Classify every factual claim into one of three bins

- **Verified:** you read it in this session — in this codebase, in fetched docs, in command
  output, or by running it. → Act on it; state it as fact.
- **Confident recall:** stable, universally replicated knowledge (Python list semantics, HTTP
  status codes, SQL join behavior, POSIX basics). → Act on it; no hedge.
- **Plausible reconstruction:** exact API signatures, parameter names, CLI flags, config keys,
  default values, version-specific behavior, anything in a library that moves fast or is
  younger than your training data. → **Do NOT act on it as-is.** Verify (Step 2) or flag
  (Step 3).

**The tell for bin 3:** the detail is *specific* (an exact name, an exact flag) and your source
is "it's usually something like this". Specificity without a source is where hallucinated APIs
come from. When in doubt between bins 2 and 3, treat as 3 — the check costs seconds.

## Step 2: The verification ladder (cheapest rung first)

1. **This codebase:** grep for existing usage of the API. The repo is ground truth for how
   it's called *here* — version, style, and wrappers included.
2. **Installed source:** read the signature in `node_modules` / site-packages / vendor / the
   crate source; or run `python -c "help(x)"`, `tool --help`, `man tool`.
3. **A 10-second experiment:** run the one-liner in a REPL or scratch script. Executing beats
   reading — it verifies the whole stack, not just the signature.
4. **Current docs:** fetch documentation (docs MCP / official site / web search) when the
   library is newer than your knowledge or the behavior is version-sensitive. Check the
   installed version in the lockfile FIRST so you read the right docs.
5. **No rung available** (offline, no env): write the code anyway, but mark it — Step 3.

## Step 3: Communicating uncertainty without drowning the signal

1. Hedge ONLY load-bearing uncertainty. A response that hedges everything hides the one hedge
   that matters. Verified and confident-recall facts are stated plainly.
2. Format for a real unknown — best answer + confidence + concrete check:
   > "`bulk_create` should batch these into one query — verify the generated SQL with
   > `echo=True`; this differs across ORM versions."
3. Never invent a citation, version number, benchmark figure, or API name to make an answer
   look complete. "I don't know the exact flag — check `tool --help`" is a correct and
   complete answer.
4. In code you couldn't verify, leave the marker at the call site:
   `# UNVERIFIED: confirm param name against installed vX.Y` — so the reader knows exactly
   where the risk sits.

## Step 4: Assumption bookkeeping

When you proceed on an assumption, record it AT THE MOMENT you make it (note file, todo, or
message), and restate ALL assumptions in one compact block in your final message
("Assumptions: X; Y; Z"). An assumption mentioned once at step 2 of 14 is invisible by
delivery time — the final block is what the user actually reads.

## Checklist — run before delivering any code that touches a library

- [ ] Every imported function/method I call: seen in this repo, in installed source, in
      fetched docs, or in a REPL this session?
- [ ] Every CLI flag and config key: confirmed against `--help` or docs for the INSTALLED
      version?
- [ ] Every number I quoted (limits, defaults, versions, prices): has a source, or is flagged?
- [ ] Anything remaining unverified: explicitly marked at the call site AND in the report?

## Worked example — weak vs. correct

Task: "Use the `stripe` library to create a subscription with a 14-day trial."

Weak: write `stripe.Subscription.create(customer=cid, trial_days=14, plan=pid)` from memory.
(`trial_days` and `plan` are plausible reconstructions — one is renamed, the other deprecated;
it fails at runtime, in production, on a payment path.)

Correct: (1) grep the repo — two existing `Subscription.create` calls use `items=[...]` and
the wrapper `billing/client.py`; (2) check installed version in the lockfile; (3) confirm the
trial parameter in that version's source/docs → `trial_period_days`. Deliver using the repo's
own wrapper, and state: "Used `trial_period_days` per stripe-python vN.N (verified against
installed package)."

## Done when

Every bin-3 claim in the deliverable has either climbed the verification ladder to "verified"
or carries an explicit UNVERIFIED marker with the exact check the reader should run; the final
message contains the consolidated assumptions block; and nothing in your output states a
reconstructed specific as fact.
