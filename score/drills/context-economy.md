---
name: context-economy
description: Protect the context window as a scarce resource — read at the right altitude, delegate bulk reconnaissance to subagents so only conclusions enter the main thread, externalize durable facts to disk, and respond to your own degradation signals. Trigger this when about to read a large file or many files, when a search/log-dig would flood the conversation with content you won't reference again, when deciding whether to delegate to a subagent, and whenever you notice re-running searches or re-deriving established facts. Do NOT confuse with session-state-management (which owns the WORKING_NOTES.md file and resume protocol — this skill decides what enters context at all) or incremental-delivery (which chunks the deliverable — this skill budgets the reading around it).
---

# Context Economy

Everything you read enters the same window your reasoning runs in. Fill it with noise and the
noise wins: instructions decay, early decisions blur, retrieval degrades — and output quality
collapses without any error message announcing it. An advanced model husbands its context
implicitly; you do it as explicit procedure.

## Rule 1: Read at the right altitude

Match reading depth to need, before opening anything:

| Need | Action |
|------|--------|
| One fact ("does X call Y?", "what's the version?") | grep / targeted search — never open the file |
| Call something correctly | Read the signature + one existing call site, not the whole module |
| Edit a file | Read it fully (non-negotiable — Prime Directive 2) |
| Understand a subsystem's shape | Symbol map / headings / one representative flow — not every file |
| Judge a large artifact (logs, datasets) | Head/tail/sample + targeted filters, never the whole thing |

The violation to catch: opening a 2,000-line file to answer a one-line question. Ask "what is
the smallest read that answers this?" before every Read.

## Rule 2: Delegate bulk work to protect the main thread

When a task requires sweeping many files, digging long logs, or broad reconnaissance whose raw
content you will NOT reference again: hand it to a subagent. The subagent burns its own context
on the haystack and returns only the needle. The main conversation stays at decision altitude.

Delegation test — delegate when ALL of: the raw material is large, only the conclusion matters
downstream, and the sub-task is separable with a crisp question. Don't delegate when you'll
need the raw content in-thread anyway, or the task is a two-minute look.

This is the primary reason to delegate, beyond parallelism: context preservation.

## Rule 3: Don't re-read what hasn't changed

If you read a file this session and it's unchanged, trust your knowledge and your notes.
Re-read only when: someone else (user, formatter, another agent) may have modified it, an edit
of yours failed unexpectedly, or you've had a context loss. Redundant re-reads are pure
context burn.

## Rule 4: Externalize durable facts the moment they matter

Decisions, discovered constraints, findings, and todo state go to disk (WORKING_NOTES.md, a
scratchpad file) when they're established — not "later", and not only when compaction looms.
The context window is working memory; disk is long-term memory. Facts that live only in
context die with it. (The file format and resume protocol belong to session-state-management;
this rule is about WHEN to move facts out of context.)

## Rule 5: React to your own degradation signals

The signals that your context is failing you: re-running a search you already ran; re-deriving
a fact you established an hour ago; surprise at your own earlier decision; instructions from
the original request feeling new on re-read. On any of them: STOP consuming new content,
re-read the notes file, and only then continue. Pushing on from fog produces confident work
built on a forgotten foundation.

## Worked example

Task: "Find why checkout intermittently 500s — logs are in /var/log/app/ (14 files, ~2 GB)."

- Weak: `Read` the newest log → floods context with 50k lines → asks for the next file →
  by file three, the original error pattern from file one has blurred; analysis restarts.
- Context-economy:
  1. Rule 1: never open a log raw. `grep -c 'HTTP 500'` per file → the needle is in 3 files.
  2. Rule 2: delegate — subagent per file with a crisp question ("extract each 500 with the
     20 lines before it; return timestamps + the exception class only"). Three subagents burn
     their own contexts; the main thread receives ~40 lines of conclusions.
  3. Rule 4: findings ("all 500s follow a connection-pool-exhausted warning within 2s; only
     during the 02:00 batch job") go into WORKING_NOTES.md immediately.
  4. Main thread proceeds to the fix with a nearly-empty window and complete knowledge.

## Done when

Ongoing — an ambient discipline. You are following it when: nothing large was read where a
grep or a sample would answer; bulk reconnaissance ran in subagent contexts, not the main
thread; no unchanged file was re-read; every durable fact is on disk within minutes of being
established; and no degradation signal was pushed through instead of triggering a notes
re-read.
