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
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m pyngo.app
```

Abrí `http://127.0.0.1:5000`.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
ruff check src/ tests/
pyright
```
