# TRAPS — the field-proven failure catalog

Every entry below cost a real debugging loop on a production bench. They are
model-agnostic: these are properties of shells, pipelines, sandboxes, and version-control
semantics — not of any particular model. Read this file once; pattern-match forever.
Add new entries with the same shape: **trap → symptom → rule**.

## Pipelines and output

- **Tail-truncation hides failures.** `cmd | tail -N` (or `head`) on a build/test run can
  scroll the only failing line out of view; a truncated log reads as green. *Rule:*
  capture the full log to a file, then grep for `error|FAILED|Executed` — never judge
  from a window.
- **Pipes mask exit codes.** `failing-cmd | tail -3; echo exit=$?` reports the *tail's*
  exit. *Rule:* check `${PIPESTATUS[0]}` (bash) / `$pipestatus[1]` (zsh), or write to a
  file and test the command directly.
- **`grep -m1` SIGPIPEs long-running producers.** Grabbing the first event line from a
  streaming process kills the producer mid-run when grep exits. *Rule:* stream to a file;
  grep the file afterwards.
- **Background compounds without `set -e` swallow failures silently.** A failed mutation
  step (an assert, a bad anchor) lets every downstream step run against the unchanged
  tree — the run "completes" having done nothing. *Rule:* mutations run foreground with
  verification of their effect (read the emitted artifact) before anything depends on them.

## Premises and verification

- **Grep-era premises die.** A finding from an old scan ("X has no Y") is a hypothesis,
  not a fact — code moves. *Rule:* re-verify every load-bearing premise at task start, in
  the current tree; record premise-death as a real outcome that kills the lane, not the goal.
- **Partial sweeps report as clean.** A verification loop that throws on entry 3 of 8
  never checks 4–8, and its output looks like a pass for what it printed. *Rule:*
  verification loops are exception-proof per item and print an explicit verdict per item.
- **The proof can mutate the artifact.** Exercising a cache/index/store to prove it works
  (e.g. an offline package-install dry run) may touch metadata and invalidate the very
  digest you pinned beforehand. *Rule:* pin **after** the proof, never before.
- **"Exists" is not "loadable"; "committed" is not "verified".** A directory being present,
  a hash matching, a commit landing — none of these prove the thing works. *Rule:* verify
  at the level of the claim: run it, load it, open it as the user would.

## Version control and digests

- **Working tree ≠ checkout.** A digest of your working copy includes untracked nests
  (caches, generated state) that a clean checkout will not have; the same tree hashes two
  ways. *Rule:* for tracked inputs, pin the `git archive` digest of the remote tip AND
  make the working tree match it; for ignored/generated inputs, pin the working copy —
  know which regime each input is in.
- **Name-based resolution picks stale twins.** Resolvers that select by name (signing
  identities, provisioning profiles, config files) grab whichever same-named copy they
  find first. *Rule:* pin by content identity (hash, serial, uuid) and evict stale
  same-name copies.
- **Generated files inside tracked trees drift.** Regenerating a project/scaffold changes
  its digest even with identical inputs when the generator or environment differs.
  *Rule:* pin what the consumer will actually measure, from the environment that will
  measure it.

## Sandboxes and delegated work

- **Sandbox failures are environment, not regression — but prove it.** Nested-sandbox
  denials, headless pasteboard/audio/simulator failures, cache-write refusals: delegated
  runs fail these while the code is fine. *Rule:* re-run the same suite on the host
  before believing either verdict; keep a list of your bench's known artifact classes.
- **Delegate reports are advisory.** Pasted test output proves nothing. *Rule:* the
  conductor re-runs proof commands and reads the full diff plus `git status` — scope
  creep is a finding even when the code is good.
- **A silent lane at ~0 CPU is blocked, not thinking.** *Rule:* check the process table
  and its open fds before waiting on it; find what it's actually waiting for.

## Tools and environments

- **Interactive CLIs hang headless.** Tools that read stdin block forever under a
  non-TTY driver without explicit EOF (`< /dev/null` or a heredoc). *Rule:* every
  headless invocation states its stdin.
- **Ambient environment leaks into builds.** Exported identities/paths from earlier work
  silently override per-run config. *Rule:* launch consequential pipelines with an
  explicit environment (`env -u VAR ...`), not whatever the shell accumulated.
- **Installers and binaries vanish.** Disk cleanups delete tool payloads behind intact
  symlinks. *Rule:* `which` + `--version` before concluding anything about a tool, and
  before concluding it's *missing*, too — prove absence the same way you'd prove presence.
- **Nested heredocs collide.** A heredoc whose *content* contains the outer delimiter
  terminates early and parses garbage. *Rule:* unique delimiters, or write files with a
  proper file-writing tool instead of shell quoting.

## Claims and delivery

- **State claims at the level verified.** Green unit tests are not evidence for a
  user-facing claim; a successful build is not a successful launch. *Rule:* before
  "done/fixed/shipped" on anything a human touches, exercise it the way the human will —
  or name exactly what remains unverified.
- **Silent caps read as full coverage.** Any bounded sweep (top-N, sampled, first-match)
  that doesn't announce what it dropped will be read as exhaustive. *Rule:* log what was
  not covered, every time.
