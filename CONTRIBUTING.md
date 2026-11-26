# Contributing

Thanks for reading the code. Pyngo is didactic material, so the first rule is
that the code must be explainable out loud, line by line.

## Setup

```bash
git clone https://github.com/jsvdr/pyngoc.git
cd pyngoc
uv sync
uv run pre-commit install
```

`uv sync` creates `.venv` with Python 3.12 (from `.python-version`) and
installs the dev group.

## Before opening a pull request

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

All four must pass. `pre-commit` runs the same tools for you; CI repeats them
on Python 3.12, 3.13 and 3.14.

The security jobs are cheap to reproduce:

```bash
uv export --frozen --no-dev --no-emit-project --format requirements-txt -o /tmp/req.txt
uvx pip-audit -r /tmp/req.txt
uvx bandit -q -r src/pyngo
uvx semgrep --config p/python --error src/pyngo
```

## Fuzzing

```bash
uv sync --group fuzz
uv run python tests/fuzz/fuzz_compiler.py -max_total_time=60 tests/fuzz/corpus
```

Every phase must answer with an error, never with a traceback. If it crashes,
the input is written as `crash-*`: fix the bug, then copy that file into
`tests/fuzz/corpus/` so it is tried again on every run.

## The Go executor

`tools/pyngo-run` is its own Go module and has no dependencies outside the
standard library:

```bash
cd tools/pyngo-run
gofmt -l .        # must print nothing
go vet ./...
go test ./...
```

Its golden files are real compiler output; regenerate them when the object
code changes:

```bash
uv run pyngo build examples/loop.pyn --json > tools/pyngo-run/testdata/loop.json
uv run pyngo build tools/pyngo-run/testdata/if.pyn --json > tools/pyngo-run/testdata/if.json
```

Then update the expected output and step count in `machine_test.go`.

## Style

- Everything in the repository is in English: identifiers, comments, error
  messages, UI text, documentation and commit messages.
- Comments explain *why*, in one line, next to the line they describe.
- No new dependency without a reason: the only runtime ones are Flask and
  gunicorn.
- The duplication between `var_decl` and `assignment`, and between the four
  token walkers, is intentional. Each method reads like its production.
- Fixed messages (`Syntax OK`, `Semantic OK`, `Line X: TYPE ERROR: …`) are
  compared by tests. Do not reword them casually.

## Commits

Conventional-ish prefixes, in English:

```text
feat: add the object code panel
fix: read the print argument through BP
refactor: rename the encoder tables
test: cover 8-bit division
docs: explain the IR limitations
ci: cache the uv environment
build: pin Python 3.12
```

## Adding a language feature

1. Update [`docs/grammar.md`](docs/grammar.md).
2. Update `src/pyngo/parser.py` and `src/pyngo/semantic.py` (same shape).
3. Update `src/pyngo/ir.py` and `src/pyngo/codegen.py`.
4. Add a unit test in `tests/` and, if the feature changes the semantics, a
   program shape in `tests/differential/generator.py`.
5. Run the four commands above.

## Reporting bugs

Open an issue with the smallest program that reproduces the problem, the
button you pressed (or the command you ran) and the output you expected.
Security issues: see [`SECURITY.md`](SECURITY.md).
