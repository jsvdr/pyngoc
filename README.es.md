# Pyngo

Compilador didáctico por fases: lexer → parser → análisis semántico → código
intermedio → código objeto x86 de 16 bits. El lenguaje tiene `int` y `bool`,
`if` / `while` / `print` y los operadores `@` (suma), `#` (resta), `&`
(multiplicación), `|` (división), `==`, `>` y `<`.

El backend es Flask y el frontend es HTML/CSS/JS sin frameworks. El código está
escrito para leerse de arriba a abajo, sin AST.

**La documentación completa está en inglés**, en [`README.md`](README.md).
Este archivo es solo un resumen para quien llegue desde el español.

## Correrlo

```bash
uv sync
uv run pyngo serve        # → http://127.0.0.1:5000
```

Compilar un archivo desde la terminal:

```bash
uv run pyngo build examples/loop.pyn
uv run pyngo check examples/loop.pyn
```

## Pruebas

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Las pruebas incluyen 300 programas aleatorios (semilla fija) que se compilan,
se ejecutan en un emulador x86 de 16 bits y se comparan contra un intérprete de
referencia independiente.

## Documentación

- [`docs/grammar.md`](docs/grammar.md) — la gramática.
- [`docs/errors.md`](docs/errors.md) — cómo se detecta cada error.
- [`docs/architecture.md`](docs/architecture.md) — módulos y diagrama.
- [`docs/limitations.md`](docs/limitations.md) — lo que el compilador no hace.

## Licencia

MIT.
