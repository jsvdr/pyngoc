# Pyngo — compilador didáctico

Compilador por fases (scanner → parser → semántico → código intermedio)
para un lenguaje propio con `int`/`bool`, `if`/`for`/`print` y operadores
`@ # & | == > <`. Backend en Flask, frontend vanilla, sin dependencias de más.
Código simple a propósito: se lee de arriba a abajo, sin AST.

## Cómo correrlo (Python 3.12)

```bash
pip install -r requirements.txt
python backend/app.py
```

Abre `http://127.0.0.1:5000`. Desarrollo con recarga: `FLASK_DEBUG=1`.

## Cómo revisarlo

```bash
pytest tests/ -q
ruff check backend/ tests/
ruff format --check backend/ tests/
pyright
```

## Fases (un botón por fase en la GUI)

| Botón | Ruta | Salida OK |
|---|---|---|
| TOKENS | `POST /analizar` | lista de tokens |
| Parser | `POST /parser` | `Syntax OK` |
| Semántico | `POST /semantico` | `Semantic OK` |
| CI | `POST /intermedio` | `nombre DW/DB ?` |

## Ejemplo para probar

```text
{
    int contador = 1;
    bool activo = true;
    contador = contador @ 1;
}
```

## Estructura

```text
backend/   tokens.py scanner.py parser.py semantico.py intermedio.py app.py
frontend/  index.html script.js style.css
tests/     test_smoke.py (5 casos)
```
