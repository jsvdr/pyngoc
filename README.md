# Pyngo — compilador didáctico

Compilador por fases (scanner → parser → semántico → código intermedio)
para un lenguaje propio con `int`/`bool`, `if`/`while`/`print` y operadores
`@ # & | == > <`. Backend en Flask, frontend vanilla, sin dependencias de más.
Código simple a propósito: se lee de arriba a abajo, sin AST.

La gramática del lenguaje está en [`docs/gramatica.md`](docs/gramatica.md)
y el catálogo de errores en [`docs/errores.md`](docs/errores.md).

## Estado

| Fase | Estado |
|---|---|
| Scanner | ✅ |
| Parser (sin AST) | ✅ |
| Semántico | ✅ |
| Código intermedio (TASM) | ✅ |
| Optimizador | ⏳ por definir |
| Código máquina | ⏳ por definir |

## Cómo correrlo (Python 3.12)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python backend/app.py
```

Abre `http://127.0.0.1:5000`. Desarrollo con recarga: `FLASK_DEBUG=1`.
Si el puerto está ocupado: `PORT=5001 python backend/app.py`.

## Con Docker (sin instalar Python)

```bash
docker build -t pyngo .
docker run -p 5000:5000 pyngo
```

## Cómo revisarlo (si algo falla, corre esto primero)

```bash
pip install -r requirements-dev.txt
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
| CI | `POST /intermedio` | tabla Nombre/Operador/Atributo |

## Código intermedio (CI)

El CI se pinta como tabla **Nombre / Operador / Atributo**. El generador arma
líneas TASM (`MOV AX, a`) y al final las parte en esas 3 columnas.

Versión sencilla: cada expresión se calcula en `AX` y solo se admiten
**operandos simples** (variable, número o `true`/`false`), pero se pueden
encadenar operaciones del mismo nivel:

- `a @ b @ c` → `ADD AX, b` / `ADD AX, c`
- `a & b | c` → `MUL BX` / `DIV BX`
- `while (a < b) { ... }` → etiqueta al inicio, `CMP` + salto, `JMP` de vuelta
- los `bool` son `DB`: se cargan con `MOV AL` + `MOV AH, 0` y se comparan con `CMP AL`
- `print(x)` parte el valor en `COC` (decenas) y `RESI` (unidades) y los imprime
  con `INT 21H` / `AH=02H`; un literal fuera de 0–99 se rechaza con un error
  claro, porque la plantilla imprime 2 cifras

Si hiciera falta la pila (por ejemplo `a @ b & c` o `( a @ b )`), el botón CI
muestra un error claro en vez de generar código.

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
tests/     test_smoke.py (casos de humo)
docs/      gramatica.md errores.md
```
