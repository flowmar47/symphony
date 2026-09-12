---
name: symphony
description: Orchestrate substantial work across available models and reasoning efforts. Use when asked for Symphony, multi-model delegation, or coordinated parallel work; keep small tasks solo and respect the host's delegation restrictions.
---

# Symphony — one conductor, adaptable seats

Any capable host model can conduct. Assign responsibility by **role**, then select an
available model and effort for the task. No model family owns a seat permanently.
The conductor owns integration and authorized landings; delegates never commit, push,
publish, sign, spend money, or mutate release state.

## Choose the smallest useful orchestra

| Role | Responsibility | Authority |
|---|---|---|
| Conductor | Scope, routing, integration, acceptance, user communication | Only already-authorized external actions |
| Builder | Implement a bounded spec and report evidence | Explicit writable scope; no landings |
| Scout | Retrieve facts, research, inspect sources | Read-only; web only when permitted |
| Verifier | Check actual artifacts against acceptance criteria | Read-only source; scoped execution when permitted |
| Reviewer | Fresh-context critique of the design or diff | Read-only; independent of the author |

Small tasks stay solo. Parallelize independent work with disjoint ownership; serialize
dependencies and heavy shared resources. Prefer native delegation when the host exposes
suitable model/effort, permissions, ownership and completion controls. Use the CLI
fallback only when allowed and useful. **If the host or user forbids agents, stay solo:
a CLI process is not a workaround.** Do not create user-owned tasks for internal
delegation without a request.

## Select models and effort from current capabilities

1. Discover available models, supported efforts and execution constraints. For the
   Codex CLI fallback, use `scripts/symphony-models.py`, which queries public
   `model/list`; do not read private model caches or guess successor IDs.
2. Honor explicit selections. Otherwise use an accepted route for this task class or
   choose a **provisional** route from current capability guidance. Availability alone
   is not evidence of quality, affordability or task suitability.
3. Use the lowest effort supported by evidence for the task's uncertainty and risk.
   A hard problem can justify a frontier model immediately; do not waste cheap retries
   to satisfy an escalation ritual. Effort meanings differ across providers; more
   reasoning is not automatically better.
4. Record the selection and rationale. Model IDs and effort values are runtime data,
   not a release-by-release allowlist in code or this skill.

Provisional starting candidates, **not fixed rules or measured rankings**:

| Work | Candidate if available | Starting effort |
|---|---|---|
| Clear retrieval, extraction, mechanical changes | Luna | Low / medium |
| Scoped features, substantial implementation, integration | Sol | Medium / high |
| Architecture, difficult debugging, consequential review | Astra | High; deeper only with justification |

Any capable available model may fill a role. New releases become candidates, not
automatic replacements for proven routes. Keep current assignments in task records or
per-invocation configuration, not this file. Never automatically enable premium
execution or efforts that spawn nested agents: these need compatible authorization,
concurrency and time budgets. Discovery failure is not license to invent a model.

## Frontier review of delegated work

**Every return from Sol, Luna or another lower-capability model requires a separate
review by an appropriate current frontier model before acceptance or landing. Astra is
the current initial frontier choice, not a permanent model ID.** This applies to code,
plans, research and other artifacts, not just failed work. If capability is unknown,
treat the return as requiring frontier review until resolved.

Give the reviewer the actual artifact/diff, task requirements, source-bound evidence and
constraints, without priming it with the author's reasoning or desired verdict. Review
at the best justified supported effort: medium for narrow deterministic work, high for
behavioral changes or research synthesis, and a deeper available setting for difficult
architecture, security or interacting constraints. These are starting points, not
cross-model equivalence claims. Include review tokens in the total cost.

The frontier conductor may perform this review itself in a separate deliberate pass
when its capability is established; use fresh-context native review when permitted and
appropriate. Do not have the lower-capability author approve itself. A return from an
unknown model cannot be exempted by claiming it is frontier. If an appropriate reviewer
is unavailable or delegation is forbidden and the conductor cannot fill that role,
report **frontier review pending**; do not quietly accept or land the result. Frontier-
authored work still gets risk-proportionate verification and review.

## Brief once, report compactly

Every lane receives goal, acceptance criteria, exact scope, constraints, non-goals,
relevant inputs and a stop rule. Use `examples/SPEC-template.md` for CLI builders.
Include only necessary context; point to large logs instead of copying them to every
agent. Inherited host instructions still apply; a fresh brief is not a clean-room claim.

Use bounded work units and verdicts. Reports distinguish completion, partial work,
failure and checks not run, with artifact/log references. A failed lane gets at most one
precise repair attempt before conductor takeover or re-scoping. Authentication,
permissions, unavailable tools and invalid premises need diagnosis, not a more expensive
model. Use notifications or bounded waits; low CPU alone does not prove a hung process.

## Accept evidence, not assertions

Read the report, source diff and scope status. Inspect actual execution records bound
to exact source, inputs, command and environment. Reuse complete unchanged evidence;
rerun when those change or evidence is missing or unreliable. An author-pasted summary
alone is insufficient. Keep the mandatory frontier review above and final integration
checks where warranted, without duplicating every test by ritual.

Conductor landings still need authorization. Use problem-first commit/PR descriptions
and truthful model/harness attribution; label an unreported identity instead of guessing.

Execution completion is not acceptance. If validation is explicitly deferred, report
**implemented but behaviorally unvalidated** through publication. Never turn a process
exit code into verified acceptance or a savings claim.

Optimize total usage per accepted result, including failures, repairs, frontier review
and integration. Keep requested/resolved/reported model and effort distinct. Record
actual available counters, duration and retries; missing telemetry or pricing is
unknown, not zero. Do not attribute provider-rerouted work to the requested model.

## Resources — load only what this task needs

In a checkout, resource paths below are relative to the repository root (two levels
above this file). Installation places a complete package beside SKILL.md, so the same
paths resolve from the installed skill root.

- Serious multi-step work: read `score/OPERATING.md`; load individual `score/drills/`
  only when relevant. Do not copy the entire Playbook into every lane.
- CLI discovery, dispatch, repair and status: read [CLI reference](references/cli.md).
- Later assessment on real work: read [real-work assessment](references/real-work-assessment.md).
  Calibration is not a prerequisite for creating, installing or using this skill.
- Repeated operational failures: consult the relevant `score/TRAPS.md` entry.

Host/system rules and explicit user scope remain authoritative over the Score and this
skill. Optional hooks are not installed or enabled by using Symphony.
