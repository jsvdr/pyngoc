# Changelog

All notable changes to this project are documented here. The format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] — 2026-11-24

### Added

- `pyngo` command line: `pyngo build <file>`, `pyngo check <file>` and
  `pyngo serve` (`pyngo/cli.py`, entry point in `pyproject.toml`).
- `GET /healthz` endpoint for container and platform health checks.
- `render.yaml`, `Procfile` and a gunicorn-based production start.
- Differential test suite: 300 seeded random programs compiled, executed in a
  small x86-16 emulator and compared with an independent reference
  interpreter (`tests/differential/`, `tests/test_differential.py`).
- `docs/architecture.md` with a Mermaid diagram, five ADRs in `docs/adr/` and
  `docs/limitations.md`.
- GitHub Actions matrix over Python 3.12, 3.13 and 3.14, using `uv` with
  caching; Dependabot for `uv`, GitHub Actions and pre-commit.
- `pre-commit` hooks: whitespace, YAML/TOML checks, `ruff`, `ruff-format` and
  `pyright`.

### Changed

- **The whole repository is now in English**: identifiers, comments, error
  messages, UI, documentation and commit messages. A short Spanish summary is
  kept in `README.es.md`.
- Source layout moved to `src/pyngo/` (`backend/` → `src/pyngo/`,
  `frontend/` → `web/`).
- Selected modules renamed: `scanner.py` → `lexer.py`,
  `recorrido.py` → `cursor.py`, `semantico.py` → `semantic.py`,
  `intermedio.py` → `ir.py`, `codificador.py` → `encoder.py`,
  `objeto.py` → `codegen.py`.
- Error messages: `Line X: ERROR DE TIPO` → `Line X: TYPE ERROR`,
  `ERROR DE DECLARACIÓN` → `Line X: DECLARATION ERROR`,
  `ERROR DE CÓDIGO OBJETO` → `Line X: OBJECT CODE ERROR`;
  `Sintaxis OK` → `Syntax OK`, `Semántico OK` → `Semantic OK`.
- Packaging: `uv` with `pyproject.toml`, `uv.lock` and `.python-version`
  replace `requirements.txt` / `requirements-dev.txt`.
- The `print` routine now reads its argument through `BP` (`MOV BP, SP` /
  `MOV AX, [BP+2]`), so it addresses the stack segment instead of the data
  segment.

### Fixed

- `print ( x )` printed the wrong value when the argument had been pushed,
  because `MOV BX, SP` plus `[BX+2]` reads `DS:`, not the stack.

## [1.1] — 2026-11-16

### Added

- Object-code phase: `DATA` and `CODE` panels with address, content and hex.
- `print` in object code, using `DIV DL`, `TENS`/`ONES` and `INT 21H`.

Earlier work (lexer, parser, semantic analyzer, intermediate code and the
Flask GUI) was developed before the first tag, so it has no entry here.

[1.2.0]: https://github.com/jsvdr/pyngoc/compare/v1.1...v1.2.0
[1.1]: https://github.com/jsvdr/pyngoc/releases/tag/v1.1
