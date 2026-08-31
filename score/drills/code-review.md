---
name: code-review
description: Review a diff or pull request — including your own before delivery — in a fixed pass order (correctness, then safety/security, then design, then style) and report findings ranked by severity. Trigger this when asked to review a PR or diff, when checking over a change before committing or handing it off, and as the design-and-correctness half of your own pre-delivery review. Do NOT trigger for the mechanical did-it-run gate (use verification-and-review) or for a dedicated vulnerability sweep (use security-review, which this skill's safety pass defers to) — this skill is holistic human-style review of a change set.
---

# Code Review

Review in order of what costs most to get wrong. A style nit found while a correctness bug
goes unnoticed is a review that failed. Do the passes in sequence — do not let a formatting
distraction pull you off the correctness pass.

## Setup: get the whole diff and its intent

1. Read the full change set (`git diff <base>...HEAD`, or the PR diff) — not just the latest
   commit. Review the change as it will land.
2. Know the intent: the PR description, the linked issue, or the task. A diff can be
   internally perfect and still wrong — because it does the wrong thing. Judge against intent.
3. Read big diffs in dependency order (types → logic → interfaces), not file-alphabetical.

## Pass 1: Correctness (highest priority)

For each hunk ask:
- Does it do what the intent says? Are all stated requirements actually met by this diff?
- Edge cases: empty inputs, boundaries (off-by-one, `<` vs `<=`), null vs empty vs zero,
  duplicates, malformed input. Walk the same edge list as verification-and-review against the
  new code.
- Logic errors: inverted conditions, wrong operator, wrong variable, swapped arguments,
  incorrect loop bounds, mishandled async (unawaited promises, missing error propagation).
- Are there tests, and do they assert concrete behavior (not just "ran without throwing")?
  Does a test exist for the bug this PR claims to fix, failing on the old code?

## Pass 2: Safety and security

- Trust boundaries: is new external input validated? New sinks (query, command, path, HTML,
  deserializer) safe? If the diff touches auth, input handling, or sensitive data, run the
  full security-review checklist rather than a glance.
- Failure behavior: fallible operations handled, not silently swallowed; errors carry context;
  resources cleaned up on all paths.
- Secrets: none introduced in code or fixtures. Concurrency: new shared state or check-then-act
  races? Data safety: migrations reversible, destructive operations guarded.

## Pass 3: Design

- Right place: does the change belong where it was put, following the codebase's existing
  patterns? Or does it fight them / duplicate an existing utility?
- Scope: does the diff exceed its intent (drive-by refactors, unrelated changes)? Flag scope
  creep — it's a review finding, not a courtesy.
- Complexity: simpler equivalent available? Speculative abstraction (interface with one impl,
  config for a constant) to cut? Duplication that should be extracted (rule of three)?
- Interfaces: are new public signatures/names clear and consistent with the codebase? Any
  breaking change to an existing contract, intended or accidental?

## Pass 4: Style (lowest priority)

Naming clarity, comment quality (why-not-what, no process narration), formatting consistency.
**Rule:** never let Pass 4 findings crowd out or outnumber Pass 1–2 findings in the report.
If the linter enforces it, don't hand-review it — say "linter covers formatting" and move on.

## Reporting

Rank by severity, most severe first. Each finding: `file:line`, what's wrong, why it matters
(the failure it causes), and a concrete fix or a specific question.

- **CRITICAL** — will break in production / security hole / data loss. Must fix before merge.
- **HIGH** — bug under realistic conditions, missing error handling on a real path,
  requirement unmet. Fix before merge.
- **MEDIUM** — design smell, missing test, scope creep, maintainability drag. Should fix.
- **LOW** — style, naming, nit. Optional.

End with a one-line verdict: approve / approve-with-nits / changes-requested, and the count by
severity. If there are zero substantive findings, say so plainly — don't manufacture nits to
look thorough.

## Reviewing your own diff

Same passes, plus: read it as a stranger's (you're blind to your own intent — lean on the
written requirements instead), and specifically hunt your signature failure modes: unverified
API calls stated as correct, requirements quietly narrowed, success implied without a run.
Collect all findings in one read-through before fixing any — fixing mid-read hides structural
problems.

## Worked example finding

```
HIGH  src/auth/session.ts:88  Missing expiry check
  refreshSession() issues a new token whenever the old one decodes, without checking exp.
  An expired token still refreshes → sessions never actually expire (defeats the timeout the
  PR's issue asks for — requirement unmet).
  Fix: reject when payload.exp < now() before issuing; add a test with an expired token
  asserting 401.
```

## Done when

All four passes ran in order over the complete diff judged against its stated intent; findings
are ranked by severity with file:line, impact, and a concrete fix; Pass 1–2 findings are not
buried under Pass 4 nits; and the report ends with an explicit verdict and severity counts.
For your own work, the signature-failure-mode hunt was done before delivery.
