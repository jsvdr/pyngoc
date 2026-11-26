# Security policy

Pyngo is a didactic compiler. It has no user accounts, no database, no secrets
and no stored programs. The only untrusted input is the text typed or POSTed
into the web UI.

## Reporting a vulnerability

Open a private Issue in this repository describing the problem and how to
reproduce it. We will respond within 90 days.

## Scope

- `src/pyngo/app.py` — the HTTP surface (`127.0.0.1:5000` locally, `0.0.0.0`
  in containers)
- `src/pyngo/{lexer,parser,semantic,ir,codegen,encoder}.py` — they receive the
  pasted text indirectly and must not raise on it
- `web/` — the page that sends the text
- Dependencies pinned in `pyproject.toml` / `uv.lock`
- `Dockerfile` — the image that runs it

## What the app does with untrusted input

1. Flask rejects a body over 64 KB with a JSON `413` before the view runs.
2. `read_source` accepts only a JSON object with a string `source`; anything
   else is a JSON `400`.
3. The text goes through lexer → parser → semantic → IR → object code. User
   programs are **never executed** by Python: the only executor in the
   repository is the x86-16 emulator under `tests/`.
4. A deeply nested expression is a syntax error
   (`Line X: The program is nested too deeply.`), not a crash.
5. A number that does not fit in 16 bits is a type error; the check looks at
   the length first, so `int()` never sees a 5000-digit string.

## Threat model

| Threat | What happens now |
|---|---|
| Injected HTML in the page | The UI paints every value with `textContent`. The CSP also forbids inline script: `default-src 'none'; script-src 'self'`. |
| Clickjacking | `X-Frame-Options: DENY` and `frame-ancestors 'none'`. |
| MIME sniffing | `X-Content-Type-Options: nosniff`. |
| Leaking the URL of a pasted program | `Referrer-Policy: no-referrer`; analysis answers use `Cache-Control: no-store`. |
| Huge request body | `MAX_CONTENT_LENGTH = 64 KB` → JSON `413`. |
| Deep recursion / stack exhaustion | Caught in `Parser.analyze`; the HTTP layer also maps any escaped `RecursionError` to a JSON `400`. |
| Huge integer literal | Length check before conversion → `TYPE ERROR`, never `ValueError`. |
| Code execution through the debugger | `FLASK_DEBUG` is off by default and the app listens on `127.0.0.1`. Never set it in production. |
| Compromised dependency | `pip-audit` audits the exported lock in CI; Trivy scans the built image. |
| Vulnerable base image | The same Trivy job fails on HIGH/CRITICAL fixes, and the base image is rebuilt on every push. |
| Container breakout | The image runs as uid 10001, needs no writable path and can run with `--read-only --tmpfs /tmp`. |
| Malformed input crashing a phase | An Atheris target sends arbitrary bytes through every phase and into the emulator; CI runs it for two minutes per push and ten per week. |

## Known limitations (honest list)

- **No authentication and no per-IP rate limit.** The public demo is a free
  Render instance; anyone can use its CPU. The work per request is small, but
  a determined client can keep it busy. Render's free plan sleeps on its own.
- **The 64 KB limit is on the body, not on time.** A large but valid program
  still takes CPU proportional to its size (milliseconds, not seconds).
- **No WAF and no TLS termination in the app.** Render (or the reverse proxy
  in front) terminates TLS; HSTS is sent by the app.
- **The fuzzer has not proven absence of bugs.** The target has run for
  hundreds of thousands of executions without a crash after the two fixes
  above, which is evidence, not a proof.

## Verifying the controls yourself

```bash
uv run pytest tests/test_app.py          # headers, 413, 400, no-store
uv sync --group fuzz
uv run python tests/fuzz/fuzz_compiler.py -max_total_time=60 tests/fuzz/corpus
uvx bandit -q -r src/pyngo
uvx semgrep --config p/python --error src/pyngo
```

The CI workflows are [`.github/workflows/security.yml`](.github/workflows/security.yml)
and [`.github/workflows/fuzz.yml`](.github/workflows/fuzz.yml).
