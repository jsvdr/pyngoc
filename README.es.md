# Pyngo

Compilador didáctico por fases: lexer → parser → semántico → código intermedio
→ código objeto x86 de 16 bits. El lenguaje tiene `int`/`bool`,
`if`/`while`/`print` y los operadores `@ # & | == > <`. El backend es Flask y
el frontend es HTML/CSS/JS sin frameworks. El código está escrito para leerse
de arriba a abajo, sin AST.

La documentación completa está en inglés en [`README.md`](README.md).
La gramática está en [`docs/grammar.md`](docs/grammar.md).

## Correrlo

```bash
uv sync
uv run pyngo serve
```

Abrí `http://127.0.0.1:5000`.

Compilar un archivo:

```bash
uv run pyngo build examples/loop.pyn
```

## Pruebas

```bash
uv run pytest -q
uv run ruff check .
uv run pyright
```
