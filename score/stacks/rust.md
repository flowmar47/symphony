# Stack Standards — Rust

Opinionated, concrete standards for Rust work (workspaces, CLIs, daemons, libraries). Applies
on top of PLAYBOOK.md and the skills. When the crate you're in already has a convention, it
wins over this file.

## Project structure

- Workspace with one crate per bounded concern; shared types in a `-core`/`-types` crate that
  leaf crates depend on, never the reverse. Binaries (`src/main.rs`) stay thin — parse args,
  wire dependencies, call into the library crate; all real logic lives in `lib.rs` and modules
  so it's testable without spawning the binary.
- Modules by domain (`vault`, `embedder`, `index`), not by layer (`models`, `utils`). A
  `utils` module is a smell — name it for what it does.
- One public API surface per crate, re-exported from `lib.rs`. Keep internals `pub(crate)`.

## Naming and idioms

- `snake_case` functions/vars, `CamelCase` types, `SCREAMING_SNAKE_CASE` consts. Constructors
  named `new`; fallible ones `try_new`. Conversions via `From`/`TryFrom`, not ad-hoc `to_x`.
- Take `&str`/`&[T]`/`impl AsRef<Path>` in public function args, not `String`/`Vec`/`PathBuf` —
  let the caller decide ownership. Return owned types.
- Iterators over index loops; `?` over `match` on every `Result`; `if let`/`let else` over
  nested matching. `let else` for early-return guard clauses.
- Derive liberally (`Debug`, `Clone`, `PartialEq`); derive `Copy` only for genuinely
  copy-cheap types.

## Idioms to AVOID

- `.unwrap()` / `.expect()` in library code paths — permitted only in tests, `build.rs`, and
  `main` for genuinely-fatal startup errors (and there `expect` with a message, never `unwrap`).
  Every other `unwrap` is a panic waiting for the input you didn't test.
- `.clone()` to silence the borrow checker. Stop, understand the lifetime, borrow correctly;
  clone only when you've decided the copy is genuinely wanted. A clone-scattered function is a
  design you haven't finished.
- `unsafe` without a `// SAFETY:` comment proving each invariant. Default: don't. Reach for it
  only with a measured reason and the safety argument written out.
- `Rc<RefCell<>>` webs to emulate a mutable graph — usually a sign the ownership model is wrong;
  prefer indices/arenas or a redesign.
- Stringly-typed errors (`Result<T, String>`) in anything reusable.

## Error handling

- Libraries: define error types with `thiserror`; one enum per crate/module with variants that
  carry context, `#[from]` for wrapping. Callers can match on variants.
- Binaries/top level: `anyhow` (or `eyre`) for the propagate-and-report path; add context with
  `.context("loading config from {path}")` at each layer so the final report reads like a trail.
- Never `panic!` on external/user input — panics are for violated internal invariants only.
  Validate input and return `Err`.
- `Option` for absence-is-normal; `Result` for operation-can-fail. Don't collapse a meaningful
  error into `None`.

## Testing and coverage

- Unit tests in a `#[cfg(test)] mod tests` at the bottom of the module they test; integration
  tests in `tests/` exercising the public API only.
- Every bug fix gets a `#[test]` reproducing it. Behavior branches, parsers, and any
  arithmetic/index logic are never left untested.
- Deterministic tests: inject clocks and RNG (pass them in), never call `SystemTime::now()` or
  thread RNG inside logic under test. (CI determinism is a priority: identical inputs must
  produce identical test outcomes across runs — and prefer a small hand-rolled deterministic
  implementation over an immature crate for a small algorithm.)
- `#[should_panic]` only with `expected = "..."`; async tests with `#[tokio::test]`. Property
  tests (`proptest`) for parsers and serializers where the input space is large.
- Coverage target ~80% of logic via `cargo llvm-cov`, but assertion quality over line count —
  each test asserts a concrete value/state.

## Dependencies — criteria to add one

- First: does `std` do it? (`std::collections`, `std::sync`, `std::fs`.) Then: is it already
  in the tree (`cargo tree`)? Only then add.
- Prefer the ecosystem-standard, widely-depended crate (serde, tokio, clap, thiserror/anyhow,
  reqwest). Check: recent releases, healthy download count, permissive license, reasonable
  transitive footprint. Avoid pre-1.0 crates for load-bearing needs unless there's no
  alternative — and per this project's determinism stance, prefer a small hand-rolled
  deterministic implementation over an immature crate for small algorithms.
- Pin via `Cargo.lock` (committed for binaries). `cargo audit` in the verification loop.

## Verification commands (this stack)

`cargo check` (fast, per-edit) → `cargo test` (per unit) → `cargo clippy --all-targets --
all-features -- -D warnings` and `cargo fmt --check` (before delivery). Benchmarks under
`--release` only. `clippy` warnings are fixed, not allowed — an `#[allow]` carries a comment
justifying it.

## Anti-patterns → corrections

- **Blocking calls inside `async`** (`std::fs`, `std::thread::sleep`) → use the async
  equivalents (`tokio::fs`, `tokio::time::sleep`) or `spawn_blocking`; blocking the executor
  stalls every task.
- **`Vec<u8>` + manual indexing for parsing** → `&[u8]` slices with `nom`/pattern methods, or
  at least bounds-checked helpers; manual indexing panics on the truncated input.
- **Over-generic too early** (`fn f<T: Trait>` where one concrete type is ever passed) →
  concrete type until a second caller needs the generic (rule of three applies to type params
  too).
- **`mem::swap`/`take` gymnastics to satisfy the borrow checker** → usually restructure so the
  borrow scopes don't overlap; reach for `take` only when the temporary-default pattern is
  genuinely the clean expression.
- **Ignoring a `Result` with `let _ =`** on something fallible that matters → handle it;
  `let _ =` is only for genuinely-don't-care returns, with a comment if non-obvious.
