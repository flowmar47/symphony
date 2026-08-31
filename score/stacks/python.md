# Stack Standards — Python

Concrete standards for Python (services, CLIs, data/ETL, scripts). Applies on top of
PLAYBOOK.md and the skills. Existing repo conventions win over this file.

## Project structure

- `src/` layout (`src/package/`) with `pyproject.toml`; the package importable only after
  install (`uv pip install -e .` / `pip install -e .`), which catches "works on my path" bugs.
- Modules by domain, not type. One `cli.py`/entry point that is thin — argument parsing and
  wiring only; logic lives in importable functions so it's testable without invoking the CLI.
- Managed with `uv` here (fast, deterministic). Virtualenv per project; never install into
  system Python.

## Naming and idioms

- `snake_case` for functions/vars/modules, `CamelCase` for classes, `UPPER_SNAKE` for
  constants. Private-by-convention with a single leading underscore; avoid dunder-mangling.
- Prefer plain functions over classes when no state is carried. Use `@dataclass` (or pydantic
  models at boundaries) for data holders — never a bare class with an `__init__` that only
  assigns attributes.
- Comprehensions and generators over manual `append` loops; generators for large/streamed data
  so you don't materialize a million-row list. `pathlib.Path` over `os.path` string joining.
  f-strings over `%`/`.format`. Context managers (`with`) for every resource.
- `enumerate`/`zip`/`items()` over index bookkeeping. `in` for membership. EAFP
  (try/except) over LBYL (pre-checking) where it's the Pythonic fit.

## Type hints

- Annotate all public function signatures and dataclass fields. Run a type checker (`mypy` or
  `pyright`) in strict mode on new code — untyped Python rots into runtime surprises.
- `X | None` (3.10+) over `Optional[X]`; built-in generics (`list[int]`, `dict[str, T]`) over
  `typing.List`. `TypedDict`/`dataclass`/pydantic for structured dicts instead of
  `dict[str, Any]`. Avoid `Any` — it disables checking transitively.

## Error handling

- Catch the narrowest exception that applies; **bare `except:` and `except Exception: pass`
  are banned** — they swallow `KeyboardInterrupt` and hide the bug. If you truly must catch
  broad, log with context and re-raise or exit non-zero.
- Raise specific built-in exceptions (`ValueError`, `FileNotFoundError`, `KeyError`) or a small
  custom hierarchy; messages state what was attempted, the offending value, and the remedy.
- `raise ... from err` to preserve the cause chain. Never use `assert` for runtime validation
  or security checks — `-O` strips asserts; asserts are for internal invariants and tests only.
- Validate external input at the boundary with pydantic (services) or explicit checks
  (scripts); fail fast, naming the field.

## Testing and coverage

- `pytest`. Tests in `tests/`, named `test_*.py`, functions `test_<scenario>_<expectation>`.
- Fixtures for setup; `@pytest.mark.parametrize` for input tables instead of copy-pasted
  tests. `monkeypatch`/`unittest.mock` at boundaries; inject clocks/RNG rather than patching
  `datetime.now`/`random` deep in logic (determinism).
- Every test asserts a concrete value/state; `assert result` alone (truthiness) is not enough —
  assert the expected value. Bug fixes get a failing-first regression test.
- Coverage ~80% via `pytest --cov`, assertion quality over line count. For data pipelines,
  test the transform on empty input, a single row, malformed rows, and unicode.

## Preferred libraries / adding a dependency

- Stdlib first — it is large: `pathlib`, `dataclasses`, `itertools`, `functools`,
  `collections`, `json`, `csv`, `sqlite3`, `datetime`+`zoneinfo`, `secrets`, `subprocess`,
  `logging`. Reach outside only when it genuinely doesn't cover the need.
- Defaults when you do: HTTP `httpx`; validation/settings `pydantic`; CLI `typer`/`argparse`;
  data `polars`/`pandas`; ORM/DB per repo. Never hand-roll date/timezone, crypto, or CSV/JSON
  parsing — use `zoneinfo`, `secrets`/`hashlib`, `csv`/`json`.
- Criteria: not covered by stdlib or an installed dep; maintained; typed or stubbed; license
  fits. Pin in `pyproject.toml` + the `uv.lock`; `pip-audit` in the verification loop.

## Verification commands (this stack)

`ruff check` + `ruff format --check` (fast, per-edit) → `pytest tests/test_x.py -k name` (per
unit) → full `pytest` + `mypy`/`pyright` before delivery. Ruff replaces flake8/isort/black;
fix its findings rather than `# noqa` without a reason.

## Anti-patterns → corrections

- **Mutable default argument** (`def f(x, items=[])`) → default `None`, create inside:
  `items = items or []`. The shared-list bug is a classic and silent.
- **Bare `except:` / `except Exception: pass`** → catch the specific exception; if broad, log
  and re-raise. Silent swallowing hides the failure you'll debug later.
- **`assert` for validation** → `if not valid: raise ValueError(...)`. Asserts vanish under
  `-O`.
- **String-built SQL / `os.system` with user data** → parameterized queries;
  `subprocess.run([...], shell=False)`. (Injection — also a security rule.)
- **`datetime.now()` naive timestamps** → timezone-aware (`datetime.now(tz=UTC)`), store UTC;
  naive/aware mixing raises or silently misfilters.
- **Materializing huge datasets** (`rows = list(cursor)`) when streaming works → iterate the
  generator/cursor; memory blows up at production scale.
- **`from module import *`** → explicit imports; star imports poison the namespace and defeat
  tooling.
- **Logic in `if __name__ == '__main__'`** beyond a thin call → move to a function; the guard
  is a launcher, not a home for code.
