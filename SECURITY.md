# Security policy

Pyngo is a didactic compiler. It has no user data, no secrets and no
production database.

## Reporting a vulnerability

Open a private Issue in this repository describing the problem and how to
reproduce it. We will respond within 90 days.

## Scope

- `src/pyngo/app.py` (HTTP surface: `127.0.0.1:5000` locally, `0.0.0.0` in
  containers)
- Dependencies pinned in `pyproject.toml` / `uv.lock`

The rest (`lexer.py`, `parser.py`, `semantic.py`, `ir.py`, `codegen.py`,
`encoder.py`, `web/`) does not process network input directly.

## What can go wrong (quick threat model)

- **User input:** pasted text is processed on the server. It is limited to
  64 KB (`MAX_CONTENT_LENGTH`), but a deeply nested program can exhaust
  Python's recursion limit and return a 500. User code is never executed.
- **Debug mode:** `FLASK_DEBUG=1` enables the Flask debugger, which allows
  code execution from the browser. That is why the app listens only on
  `127.0.0.1` by default and debug is off. Do not expose it on a network.
- **Injection:** the frontend paints everything with `textContent`, never with
  `innerHTML`, so user code cannot inject HTML.
- **Data:** there is no database, no sessions and no authentication. There is
  nothing to leak or lose.
