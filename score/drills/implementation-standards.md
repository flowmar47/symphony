---
name: implementation-standards
description: Concrete coding conventions to apply WHILE writing or editing code — naming, function/file size, error handling, input validation, types, comments, tests, and secrets. Trigger this whenever you are about to write new code or modify existing code in any language, including tests and scripts. Do NOT trigger for choosing between designs (use architecture-decisions), for diagnosing failures (use debugging-methodology), or for the final pre-delivery check (use verification-and-review) — this skill governs the act of writing itself.
---

# Implementation Standards

Precedence when rules conflict: explicit user instruction > existing codebase convention >
this skill. Before writing anything in an existing project, read 2–3 neighboring files and
copy their naming, error style, import order, and test idiom — even where you'd personally
choose differently.

## Naming

1. Name for domain meaning, not type: `overdueInvoices`, not `invoiceList2`. No new
   abbreviations the codebase doesn't already use.
2. Functions are verbs (`fetchUser`); booleans are predicates (`is_expired`, `hasAccess`);
   collections are plural.
3. A name that needs a comment is the wrong name — rename instead of annotating.
4. Match the file's existing casing exactly, even if the repo is inconsistent elsewhere.

## Structure and size

1. One function, one thing. Describing it needs "and" → split. Soft limit ~50 lines.
2. Nesting > 3 levels → invert with early returns / guard clauses.
3. Files: one concern; split around 400 lines, always by 800.
4. Duplication rule of three: copy once freely; extract on the THIRD occurrence, not the
   second — two instances don't yet reveal the axis of variation.
5. Dead code, commented-out code, unused imports: delete on sight in files you touch. Git is
   the archive.

## Error handling

1. Every fallible operation (I/O, network, parse, subprocess) has an explicit failure story:
   propagate with added context, recover, or convert to a user-facing message. `except: pass`
   and `.catch(() => {})` are forbidden.
2. Error messages carry: what was attempted, with what input, and what to do:
   `"failed to load config {path}: {err} — run 'app init' to create one"`.
3. Catch the narrowest type that covers the case; broad catches only at the process top level,
   where they log and exit non-zero.
4. Cleanup via the language's scoped construct (context manager, `defer`, `finally`, RAII) —
   never duplicated manual cleanup on both branches.

## Input validation

1. Validate at every trust boundary — HTTP handler, CLI parse, file read, message consumer,
   env var read. Schema validation where the ecosystem provides it (zod, pydantic, serde).
2. Fail fast, naming the field and the violated constraint.
3. Interiors trust validated input — do not re-validate defensively at every layer; duplicated
   validation drifts inconsistent.

## Types

1. No escape hatches (`any`, `as unknown as`, bare `interface{}`, `unsafe`) without a comment
   naming the forcing constraint.
2. Make illegal states unrepresentable when cheap (sum type over struct-of-nullables); don't
   build type-level puzzles where a runtime check plus a test suffices.
3. Python/JS: annotate public function signatures at minimum.

## Comments

1. Comment the WHY code can't show — external constraints, protocol quirks, why the obvious
   approach fails. Never the WHAT (`# increment counter`).
2. Never narrate your editing process ("added to fix bug", "changed from previous version") —
   noise the moment it merges.
3. TODOs carry an owner or a condition: `// TODO(shaun): remove after v2 migration`.
4. Deliberate shortcuts name their ceiling and upgrade path:
   `# shortcut: global lock — per-account locks if throughput matters`.

## Tests

1. Every behavior change ships ≥1 test that fails without the change. Exempt: trivial
   one-liners. Never exempt: branches, loops, parsers, money, security.
2. Every test asserts a concrete value or state change. `toBeDefined()` / `not.toThrow()` as
   the only assertion is not a test.
3. Names state scenario + expectation: `test_expired_token_returns_401`, not `test_auth_2`.
4. Test through the public interface; reaching into internals is a design smell.
5. No inter-test dependence: any order passes.

## Secrets and configuration

1. No secrets in source, ever. Env vars or a secret manager; assert presence at startup.
2. Magic numbers become named constants when they carry meaning (`MAX_RETRIES = 3`); don't
   name obvious arithmetic.
3. A value that never varies is a constant, not a config option.

## Diff discipline

The diff contains the requested change and nothing else. No drive-by refactors, renames, or
reformatting of untouched lines — note improvement opportunities in your report instead of
doing them. Debug prints are removed before delivery.

## Worked example — weak vs. standard

Task: read a JSON config and return the port.

Weak:
```python
def get_port(f):
    try:
        return json.load(open(f))["port"]
    except:
        return 8080
```
(Leaked file handle; bare except hides typos AND missing file identically; silent default
masks misconfiguration; `f` says nothing.)

Standard:
```python
DEFAULT_PORT = 8080

def load_port(config_path: Path) -> int:
    try:
        with config_path.open() as fh:
            config = json.load(fh)
    except FileNotFoundError:
        return DEFAULT_PORT  # absent config is expected; malformed config is not
    except json.JSONDecodeError as err:
        raise ConfigError(f"invalid JSON in {config_path}: {err}") from err
    port = config.get("port", DEFAULT_PORT)
    if not isinstance(port, int) or not (0 < port < 65536):
        raise ConfigError(f"port must be 1-65535, got {port!r} in {config_path}")
    return port
```

## Done when

The code follows the file's local conventions; every fallible call has an explicit failure
story; boundaries validate and interiors trust; each new behavior has a concrete-assertion
test; no escape hatches, secrets, dead code, debug prints, or drive-by changes remain in the
diff. Then move to verification.
