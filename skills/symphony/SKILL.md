---
name: symphony
description: Use when asked for Symphony, or when a task has independent slices or a justified cheaper-band lane that must still meet frontier-quality acceptance. Not for a single bounded edit, trying a newly listed model ID, or adversarial plan/diff review (use model-loop or clodex-loop). Stay solo when the host forbids agents.
---

# Symphony — one conductor, live seats

Any capable host model can conduct. Assign **roles**, then pick a model and effort from
**this session's catalog**. No family, release, or vendor owns a seat. New frontier
releases become candidates when the host lists them; this file does not.

The conductor owns integration, acceptance, and authorized landings. Delegates never
commit, push, publish, sign, spend money, or mutate release state.

**Quality floor:** an accepted result must survive the same checks a current-frontier
model at its highest *non-delegating* effort would: requirements complete, evidence-bound,
interacting constraints handled, no silent downgrades. Cheaper lanes spend less on
well-specified slices; they do not lower the bar.

## Skip unless the orchestra earns its keep

Symphony is worth invoking when independent slices can run in parallel, or when a
cheaper band can follow a frontier-quality spec and still survive frontier review.
It is not a way to try a newly listed ID, fan a single edit across models, or replace
an adversarial plan/diff loop.

Stay solo when:

- the task is one bounded change with one owner;
- the host or user forbids agents;
- there is no live catalog, or discovery failed;
- a cheaper lane plus review would cost more than one frontier pass.

A newly listed catalog entry is a **candidate**, not a reason to reroute in-flight
work or to invoke this skill.

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
suitable model/effort, permissions, ownership, and completion controls. Use the CLI
fallback only when allowed and useful. **If the host or user forbids agents, stay solo:
a CLI process is not a workaround.** Do not create user-owned tasks for internal
delegation without a request. Symphony is authorization to select models/efforts for
internal lanes; still honor explicit user pins.

## Discover, then classify — never reuse remembered names

1. Read the **live** catalog this session. Native hosts: the current subagent/model
   list on the delegation tool (IDs, effort/thinking suffixes, descriptions). Codex CLI:
   `scripts/symphony-models.py` (`model/list` only). Do not read private caches, guess
   successor IDs, or copy names out of this skill.
2. Honor explicit user/env selections if they are in the catalog. Otherwise reuse an
   accepted route for this task class, or choose a **provisional** route. Availability
   is not evidence of quality, cost, or fit.
3. Prefer the **latest listed version of a family** when the user did not pin a version.
   Map each listed option to a **band** from host signals only (see
   [routing](references/routing.md)). Do not keep a named ranking or nickname list in this file.
4. Match **effort** to uncertainty and blast radius, using the host's actual controls
   (separate effort field, or the effort/thinking suffix on a slug). Lowest effort the
   evidence supports. A hard kernel goes to frontier immediately — do not burn cheap
   retries to satisfy an escalation ritual. More reasoning is not automatically better.
5. Record work class, band, exact ID, effort, and rationale. IDs and efforts are
   runtime data.

Work → band → starting effort (pick the cheapest catalog option that can fill the band):

| Work | Band | Starting effort |
|---|---|---|
| Retrieval, extraction, mechanical edits, bounded scouts | Fast | Low / medium |
| Spec-bound features, substantial implementation, integration | Standard | Medium / high |
| Architecture, hard debugging, security, interacting constraints, review of others | Frontier | High; max only with justification |

**Inherit the conductor's model only when that model already matches the needed band
and effort.** Frontier conductors must not inherit onto scouts; cheap conductors must
not inherit onto reviews.

Never auto-enable premium execution or efforts that spawn nested agents: those need
compatible authorization, concurrency, and time budgets. Discovery failure is not
license to invent a model. Keep current assignments in task records, not this file.
New catalog entries are candidates, not automatic replacements for proven routes.

## Hit the frontier-max bar without spending frontier-max on every slice

Savings are real only when **total** usage through acceptance beats one frontier-max
solo pass — including failures, one repair, frontier review, and integration. Missing
telemetry is unknown, not zero. Never skip review to "save" tokens.

1. **Frame on frontier (or the conductor, if it is frontier).** Write a tight spec:
   goal, acceptance criteria, exact scope, constraints, non-goals, inputs, stop rule.
   Cheaper models execute a spec; they do not invent the frame. Use
   `examples/SPEC-template.md` for CLI builders.
2. **Execute on the cheapest band that can follow that spec.** Parallelize independent
   slices in one turn. Keep hard kernels, ambiguous requirements, and security on
   frontier from the start.
3. **Review cheaper returns on frontier** at the effort the solo path would have used
   for that slice (medium for narrow deterministic work, high for behavioral/research,
   max for architecture, security, or interacting constraints). Review the artifact
   against requirements and evidence, not the author's story.
4. **Escalate on capability misses, diagnose the rest.** One precise repair, then
   conductor takeover or a stronger band. Auth, permissions, missing tools, and false
   premises need diagnosis, not a more expensive model.

If a cheap slice plus review/repair would cost more than starting on frontier, start
on frontier. If review cannot run and the conductor cannot fill that role, report
**frontier review pending** — do not accept or land.

## Frontier review of delegated work

**Every return from a Fast or Standard model, and every return whose capability is
unknown, needs a separate current-frontier review before acceptance or landing.**
This applies to code, plans, research, and other artifacts, not only failures.
Frontier is whichever live option currently has the strongest reasoning controls;
do not treat a remembered name as frontier. A return from an unknown model cannot
be exempted by claiming it is frontier. The author does not approve itself.

Give the reviewer the artifact/diff, requirements, source-bound evidence, and
constraints. Do not prime it with the author's reasoning or a desired verdict.
A frontier conductor may perform this review in a distinct deliberate pass; prefer
fresh-context native review when permitted. Frontier-authored work still gets
risk-proportionate verification.

## Brief once, report compactly

Every lane gets the spec above. Include only necessary context; point to large logs
instead of copying them. Inherited host instructions still apply; a fresh brief is
not a clean-room claim.

Use bounded work units and verdicts. Reports distinguish completion, partial work,
failure, and checks not run, with artifact/log references. Use notifications or
bounded waits; low CPU alone does not prove a hung process.

## Accept evidence, not assertions

Read the report, source diff, and scope status. Inspect execution records bound to
exact source, inputs, command, and environment. Reuse complete unchanged evidence;
rerun when those change or evidence is missing or unreliable. An author-pasted
summary alone is insufficient. Keep frontier review and final integration checks
where warranted, without duplicating every test by ritual.

Conductor landings still need authorization. Use problem-first commit/PR descriptions
and truthful model/harness attribution; label an unreported identity instead of
guessing. When talking to the user, use their naming scheme for models, not internal
slugs, unless they used slugs.

Execution completion is not acceptance. If validation is deferred, report
**implemented but behaviorally unvalidated**. Never turn a process exit code into
verified acceptance or a savings claim. Keep requested/resolved/reported model and
effort distinct. Do not attribute provider-rerouted work to the requested model.

## Resources — load only what this task needs

In a checkout, resource paths below are relative to the repository root (two levels
above this file). Installation places a complete package beside SKILL.md, so the same
paths resolve from the installed skill root.

- Band mapping, inherit rules, and dispatch records: [routing](references/routing.md).
- CLI discovery, dispatch, repair, and status: [CLI reference](references/cli.md).
- Serious multi-step work: read `score/OPERATING.md`; load individual `score/drills/`
  only when relevant. Do not copy the entire Playbook into every lane.
- Later assessment on real work: [real-work assessment](references/real-work-assessment.md).
  Calibration is not a prerequisite for creating, installing, or using this skill.
- Repeated operational failures: the relevant `score/TRAPS.md` entry.

Host/system rules and explicit user scope remain authoritative over the Score and this
skill. Optional hooks are not installed or enabled by using Symphony.
