---
name: security-review
description: Run a structured vulnerability pass over code — injection, auth/authz gaps, secrets exposure, unsafe deserialization, unvalidated boundary input, SSRF, and stack-specific classes — reporting findings by severity with concrete fixes. Trigger this after writing or modifying code that handles user input, authentication/authorization, database queries, file paths, external requests, deserialization, or secrets; before committing security-sensitive changes; and whenever the user asks for a security review or mentions handling untrusted data. Do NOT trigger for pure-internal logic with no trust boundary, or as a substitute for general code-review — this pass hunts vulnerabilities specifically.
---

# Security Review

Attackers send the inputs you didn't imagine. This pass walks the code from the attacker's
side of every trust boundary. Work the checklist concretely — for each item either point to
the line that handles it or record its absence as a finding.

## Step 1: Map the trust boundaries and data flow

List every point where external data enters: HTTP params/body/headers/cookies, CLI args,
file contents, env vars, message-queue payloads, third-party API responses, uploaded files.
For each, trace where the data GOES — into a query? a shell command? a file path? an HTML
response? a deserializer? The dangerous combination is always untrusted-source →
sensitive-sink. Find the sinks.

## Step 2: Run the vulnerability checklist

For each, find the handling line or log a finding:

1. **Injection — the sink test.** Every sink gets checked:
   - SQL/NoSQL: parameterized queries / bound params ONLY. Any string-built query with
     external data = SEC-CRITICAL. ORMs help but raw-query escape hatches don't.
   - OS command: no shelling out with interpolated input; use `execFile`/`subprocess` with an
     arg array and `shell=False`; never `shell=True` with user data.
   - Path traversal: user-influenced file paths are resolved and confirmed within an allowed
     base dir; `../` is neutralized. Never `open(base + user_input)`.
   - Template/HTML: output encoding on by default; find every raw/`dangerouslySetInnerHTML`/
     `|safe`/`v-html` sink and confirm the input is trusted or sanitized (XSS).
2. **AuthN/AuthZ.** Every non-public endpoint checks authentication AND authorization. The
   frequent hole is authz: authenticated user A can act on user B's resource (IDOR) — confirm
   ownership/role is checked against the RESOURCE, not just that someone is logged in. Never
   trust a client-supplied role/ID for access decisions.
3. **Secrets exposure.** No hardcoded keys/tokens/passwords/connection strings. No secrets in
   logs, error messages, or client responses. Stack traces and internal paths never reach the
   client (generic message out, detail to server logs).
4. **Unsafe deserialization.** No `pickle`/`yaml.load` (unsafe loader)/Java native
   deserialization/`eval`/`Function()` on untrusted data. Use safe parsers (JSON, `yaml.safe_load`).
5. **Input validation at the boundary.** Type, length, range, format validated where data
   enters, allowlist over denylist. Unbounded input (huge body, deep JSON, giant upload) is
   bounded — absence is a DoS vector.
6. **SSRF and outbound requests.** URLs built from user input for server-side fetches are
   validated against an allowlist; internal/metadata addresses (169.254.169.254, localhost,
   RFC1918) are blocked.
7. **Crypto and identifiers.** No MD5/SHA1 for passwords (use argon2/bcrypt/scrypt); tokens
   and IDs from a crypto-secure RNG (`secrets`, `crypto.randomBytes`), never `Math.random`/
   `random.random`; TLS verification never disabled.
8. **Transport and session.** State-changing endpoints protected against CSRF where
   cookie-based; auth cookies `HttpOnly`+`Secure`+`SameSite`; tokens not in `localStorage`
   if XSS is reachable.

## Step 3: Adapt to the stack

Layer the ecosystem's specific classes on top:
- **Node/TS:** prototype pollution (`Object.assign`/merge from user JSON), `child_process`
  misuse, regex catastrophic backtracking (ReDoS), missing `helmet`.
- **Python:** `yaml.load`, `subprocess(shell=True)`, `pickle`, Jinja2 SSTI, Flask `debug=True`
  in prod, `assert` used for security checks (stripped under `-O`).
- **SQL/Postgres:** dynamic SQL in functions, over-broad role grants, RLS assumed but not
  enabled.
- Run the stack's audit tool as corroboration, not substitute: `npm audit`, `pip-audit`,
  `cargo audit`, and a SAST pass (`semgrep`) if available — read findings, don't just paste them.

## Step 4: Report by severity, with fixes

Rank findings; each gets file:line, the concrete exploit ("attacker sends `?id=../../etc/passwd`
→ reads arbitrary files"), and the specific fix — not "sanitize input" but "use
`Path(base).joinpath(name).resolve()` and assert it's relative to `base`".

- **CRITICAL:** directly exploitable for data breach / RCE / auth bypass. Block delivery.
- **HIGH:** exploitable under realistic conditions (stored XSS, IDOR on sensitive data). Fix
  before merge.
- **MEDIUM:** increases attack surface, not directly exploitable (missing rate limit, verbose
  errors). Log and schedule.
- **LOW/INFO:** best-practice gaps, defense-in-depth.

## Worked example finding

```
SEC-CRITICAL  api/reports.js:47  SQL injection
  Code: db.query(`SELECT * FROM reports WHERE owner='${req.query.user}'`)
  Exploit: ?user=' OR '1'='1  → dumps all reports; ?user='; DROP TABLE... → destructive.
  Fix: db.query('SELECT * FROM reports WHERE owner = $1', [req.query.user])
  Plus (SEC-HIGH, same line): no authz — any caller reads any owner's reports. Check
  req.query.user === session.userId (or a role grant) before querying.
```

## Done when

Every external-input boundary has been traced to its sinks; every checklist item is either
tied to a handling line or logged as a finding; findings are ranked with file:line, a concrete
exploit, and a specific fix; and no CRITICAL finding is left un-flagged. Reporting is
sufficient — do not fix beyond the task's scope without saying so (integrity-guardrails rule 7).
