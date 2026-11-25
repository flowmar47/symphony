# Seat plans — how the availability question gets answered

A seat plan maps the tiers in SKILL.md to concrete engine / model / effort choices that
the user confirmed. It is bench-specific and dated; discovery replaces it every
invocation, and the question in step 3 of the procedure is asked every time. Nothing in
this file is a ranking or a permanent route.

## Asking the question

Build the **B** proposal from the current `symphony-models.py --table` output, one line
per seat, and state the reason for each choice in a few words (cost, latency, the tier's
typical work, a route that produced accepted work before). Offer **A** only when
`symphony-seat-plan.sh check` reports every seat available. Offer **C** always. Say that
the conductor keeps its own model and effort and only orchestrates, reviews and
delegates. After the answer, save it:

```sh
scripts/symphony-seat-plan.sh save - <<'EOF'
{"seats": {
  "scout":          {"engine": "<cli-engine>", "model": "<fast-model-id>",     "effort": "<low|medium>"},
  "builder-light":  {"engine": "<cli-engine>", "model": "<fast-or-std-id>",    "effort": "<medium|high>"},
  "builder-heavy":  {"engine": "<cli-engine>", "model": "<workhorse-model-id>","effort": "<high|xhigh>", "fast": true},
  "builder-native": {"engine": "native",       "model": "<host-model>",        "effort": "<medium>"},
  "verifier":       {"engine": "native",       "model": "<host-model>",        "effort": "<high>"},
  "reviewer":       {"engine": "native",       "model": "<frontier-model>",    "effort": "<high|xhigh>"}
}}
EOF
```

Seat names are free-form; keep them stable so the next **A** offer is recognisable.

## This bench, 2026-09-20

Discovered with `symphony-models.py` on that date (Codex CLI 0.155.1, agy 1.2.7, Cursor
agent 2026.09.18, Claude Code 2.1.278). The plan below is the one the owner described
for handoff realization; it is the example the SKILL.md tier table quotes.

| Seat | Tier | Route | Why |
|---|---|---|---|
| conductor | conductor | the invoking session: Fable 5.1 xhigh | orchestrates, reviews and delegates only |
| scout | economy | Codex `gpt-5.6-luna` low, or `symphony-scout` native at Fable 5.1 low | cheap retrieval with cited evidence |
| builder-light | economy | agy `gemini-3.8-flash` high | mechanical edits, scaffolding, tests from a plan |
| builder-heavy | workhorse | Cursor `cursor-grok-4.6` xhigh fast | scoped multi-file implementation with clear acceptance |
| builder-native | workhorse | `symphony-builder` native at Fable 5.1 low / medium / high by lane difficulty | lanes that benefit from the host's own tools and context |
| verifier | workhorse | `symphony-verifier` native at Fable 5.1 high | runs the named checks against the combined tree |
| reviewer | frontier | `symphony-reviewer` native at Opus 5 high or xhigh, or Codex `gpt-6-astra` | the frontier review every lower-tier return needs |

Native seats get their effort from the installed `symphony-*` definitions
(`~/.claude/agents`, linked by `install.sh`); pass a different `model` per call, and pass
`effort` per call when the host's Agent tool accepts it. For an effort the definitions do
not carry, route through the `claude` CLI engine instead, which takes `--effort` exactly.

Observed on this bench the same day, from the run records under `~/.symphony/runs`:

- agy in `--mode plan` answers from its own scratch workspace unless the lane directory
  is added; the dispatcher now passes `--add-dir` and names the directory in the prompt.
- Cursor idles about 50 s after answering, with its output buffered until exit; one
  trivial probe printed nothing within 150 s. Budget answer time plus a minute.
- `claude -p --model haiku` was served by `claude-sonnet-5`; the record shows both.
- An agy scout that reached for a shell command was auto-denied headless and returned
  nothing; agy scouts are file-read lanes, so command-requiring research goes to Codex
  or Claude scouts.

## Reassessing a plan

Change a seat when a lane class keeps producing repairs or rejected reviews, when a
cheaper route delivers accepted work of the same class, or when discovery no longer lists
the model. Follow `real-work-assessment.md`: freeze the task class and rubric, at most
two candidate trials per class, frontier review of every candidate's output, total
measured usage through acceptance. A newer release is a candidate, not a replacement.
