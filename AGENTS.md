# AGENTS.md — Pyngo

A didactic, phase-by-phase compiler. The code is written for people to read
and explain, even if that is less "professional": simplicity beats DRY and
ceremony.

## Stack and commands

- Backend: Python 3.12 + Flask (`uv sync`).
- Server: `uv run pyngo serve` → `http://127.0.0.1:5000`.
- Lint/format: `uv run ruff check .` and `uv run ruff format --check .`.
- Types: `uv run pyright` in `strict` mode (config in `pyrightconfig.json`).
- Tests: `uv run pytest -q` (must always pass; smoke tests live in
  `tests/test_compiler.py`).
- CLI: `uv run pyngo build examples/loop.pyn`.
- Frontend: vanilla HTML/CSS/JS served by Flask. Flask runs on `:5000`.

## Tests are part of the contract

- `tests/test_compiler.py` pins the exact messages of the front end.
- `tests/test_encoder.py` pins every encoding, in hex and in nibbles.
- `tests/test_codegen.py` pins addresses, bytes and the two examples.
- `tests/test_differential.py` compiles 300 seeded random programs, runs the
  bytes in `tests/differential/emulator.py` and compares them with
  `tests/differential/reference.py` (output and final variables).
  The emulator is a test tool for the emitted subset, not a general one.

## Conventions (do not change without asking)

- Everything in the repository is in English: identifiers, comments, error
  messages, UI, docs and commits. The language keywords are already English
  (`if`, `while`, `print`, `int`, `bool`, `true`, `false`).
- No AST: the parser only recognizes (no `return Node`, no `tree.py`). The
  semantic analyzer copies the parser's shape and returns types
  (`"int"`/`"bool"`, `None` = unknown because of an earlier error).
- The duplication between `var_decl` and `assignment` is intentional: each
  method reads on its own and mirrors its production. Do not extract helpers
  without being asked.
- Fixed messages: `Syntax OK`, `Semantic OK`,
  `Line X: TYPE ERROR: ...`, `Line X: DECLARATION ERROR: ...`,
  `Line X: OBJECT CODE ERROR: ...`. Tests compare them exactly.
- Grammar with `@ # & |` and `{}`, `;`. Do not change operators or
  productions without explicit confirmation.
- `symbol_table[name] = data_type` is stored even after a type error; the
  early return only happens on redeclaration. `line` is captured BEFORE
  consuming the expression. Do not "optimize" this: it avoids cascading
  errors.
- GUI: fixed 1920×1080 base scaled with `zoom`; PROGRAMS/TOKENS on top
  (528px each) and PARSER/SEMANTIC (784px); below, IR and OBJECT CODE at 50%
  each (928px), with DATA above and CODE below.
  Each phase clears only its own output (there is no Clear button). Success in
  green `#065F46`, error in red `#991B1B`, projector fonts (text/UI 22px,
  tables 20px).

## Guardrails

- `.github/workflows/` can be pushed: the token has `workflow` scope. If that
  ever fails, make that change through the GitHub web UI + `git pull`.
- Do not add dependencies, frameworks, global type hints, mandatory
  docstrings or a `src/` layout change without asking first.
- Commits in English, `feat:`/`fix:`/`ci:`/`docs:`/`refactor:`/`build:` style.

## Verification and delivery

- Do not say something works or that tests pass unless you ran the command.
  Show the command and its real output.
- If something cannot be verified, say so explicitly. "It should work" is not
  "it works".
- Do not weaken or delete tests, and do not silence errors, just to make CI
  pass.
- Do not use `push --force` or `reset --hard` without authorization.
- The code must be explainable in an exam: when there are two solutions,
  choose the one that can be defended out loud.
- When done, report: what changed, which files, which commands you ran, what
  happened and what is still pending.

## Local material (not versioned)

If `plantillas-pyngo/` exists, it is local working material. It is ignored
through `.git/info/exclude`: never add it to git, never upload it and never
quote its contents in the repository.
