---
name: research-and-verification
description: Verify version-sensitive and time-changing facts against real sources before relying on them, instead of answering from training memory that has a cutoff date. Trigger this before using any library/framework API, method signature, config option, or CLI flag you have not confirmed this session; before quoting a version, price, quota, rate limit, or model ID; when asked "what's the latest / newest way to do X"; when the project pins a specific version; and whenever a fact could have changed since your training cutoff. Do NOT trigger for stable knowledge (language syntax, algorithms, math, frozen standards) or for uncertainty about internal codebase APIs (use codebase-exploration/uncertainty-management — though the environment-first source here overlaps and is compatible).
---

# Research and Verification

Training knowledge is a snapshot with a cutoff date. For anything that changes over time, that
snapshot is a HYPOTHESIS, not a fact — and a confident-outdated answer is indistinguishable
from a confident-correct one to the reader. That indistinguishability is the whole danger.
Verify, or label the guess as a guess.

## Step 1: Classify the claim — recency trigger or stable?

**Must verify (changes over time):**
- Library/framework APIs, signatures, config keys, default values.
- Package versions; anything the project pins to a specific version.
- CLI flags and tool behavior.
- Pricing, quotas, rate limits, model names/IDs.
- Deprecations; "the current recommended way" in fast-moving ecosystems.
- Any current-events or current-status fact.

**Safe from knowledge (verify only if high-stakes):** language fundamentals and syntax,
established algorithms and data structures, mathematics, frozen format/protocol standards
(HTTP semantics, JSON grammar, SQL basics), general engineering principles.

The tell you're in "must verify": the detail is specific (an exact flag, an exact parameter
name, an exact version) and your basis is "it's usually like this". Specific + unsourced =
verify or flag.

## Step 2: Verify against the source hierarchy (most authoritative first)

1. **The actual environment — what's INSTALLED, not what's newest.** The lockfile/manifest
   version; `pip show X` / `npm ls X` / `cargo tree`; the source in `node_modules`/
   site-packages/vendor; `.d.ts` type definitions; `--help` / `man`. This is ground truth for
   THIS project. A grep of existing call sites shows how the API is actually used here.
2. **Official docs / changelog for the INSTALLED version** — fetched this session (web
   fetch/search, or a docs MCP like Context7 if connected). Read the matching version, not
   "latest".
3. **Release notes / migration guides** for the specific version jump.
4. **Reputable secondary sources**, cross-checked against each other. Forums/Q&A last, never
   as the sole source.

Stop at the first rung that answers the question authoritatively. For "how is this called in
our code", rung 1 wins. For "what changed in v3", rung 2–3.

## Step 3: Record and attribute

- Date-/version-stamp externally sourced facts in your notes and, where it matters, in the
  reply: "verified against docs for v5.2, fetched today".
- Sources conflict → prefer the more primary and more version-specific; say which you took and
  why.
- Check the INSTALLED major version before applying docs — docs for v3 applied to an installed
  v2 is a self-inflicted bug.

## Step 4: When no verification tool is available

Do not fake confidence. State it as: "unverified training knowledge, may be outdated past my
cutoff", mark it an assumption to confirm, and hand over the exact check: "confirm the flag
with `tool --help`" / "check the signature in `node_modules/x/index.d.ts`". A labeled guess is
honest and useful; an unlabeled guess presented as fact is the failure this skill exists to
prevent.

## Prohibited (each is a common, high-cost failure)

- Hallucinating plausible-sounding API signatures, config keys, or flags. The single most
  frequent failure mode — write nothing specific you can't cite or verify.
- Answering "what's the latest version / newest way to do X" from memory.
- Applying docs for a different major version than the one installed.
- Citing a source you did not actually open this session.

## Worked example

Task: "Configure the retry behavior on our HTTP client."

- Weak: from memory, write `client.retries = 3` and `retry_backoff=2.0`. (Plausible, specific,
  unsourced — the option is named `max_retries` in the installed version and backoff is
  configured via a transport object; the guess fails at runtime.)
- Strong: (1) lockfile → `httpx==0.27.0`. (2) grep the repo → an existing client is built in
  `http/client.py`; it already sets timeouts, showing the construction pattern here. (3) fetch
  httpx 0.27 docs → retries are set via `httpx.HTTPTransport(retries=3)` passed to the client,
  and backoff isn't a built-in option (needs a wrapper). Deliver using the repo's pattern +
  the transport, and state: "httpx 0.27 has no built-in backoff; retries=3 via HTTPTransport
  (verified against 0.27 docs). For exponential backoff we'd add `tenacity` or a small wrapper
  — say the word."

## Done when

Every version-sensitive fact in the deliverable was checked against rung 1 or 2 of the
hierarchy this session, or is explicitly labeled unverified-training-knowledge with the exact
check the user can run; the installed version was confirmed before applying any docs; and
nothing states a specific API/flag/version/price as fact without a source you actually opened.
