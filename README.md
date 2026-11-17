# Pyngo — compilador didáctico

[![CI](https://github.com/jsvdr/pyngoc/actions/workflows/ci.yml/badge.svg)](https://github.com/jsvdr/pyngoc/actions/workflows/ci.yml)

Compilador por fases (scanner → parser → semántico → código intermedio →
código objeto x86) para un lenguaje propio con `int`/`bool`, `if`/`while`/`print`
y operadores `@ # & | == > <`. Backend en Flask, frontend vanilla, sin
dependencias de más. Código simple a propósito: se lee de arriba a abajo, sin AST.

La gramática del lenguaje está en [`docs/gramatica.md`](docs/gramatica.md)
y el catálogo de errores en [`docs/errores.md`](docs/errores.md).

## Arquitectura

```mermaid
flowchart LR
    F["Fuente"] --> T["scanner.py<br/>tokens"]
    T --> P["parser.py<br/>sintaxis"]
    P --> S["semantico.py<br/>tipos + tabla de símbolos"]
    S --> I["intermedio.py<br/>TASM en 3 columnas"]
    S --> O["objeto.py<br/>x86 16 bits"]
    I --> G["GUI<br/>panel de la fase"]
    O --> G
```

Las fases están encadenadas: cada una recibe lo que dejó la anterior y no
comparten estado. Cada botón de la GUI (`/analizar`, `/parser`, `/semantico`,
`/intermedio`, `/objeto`) re-corre las fases previas desde el fuente; si una
falla, la que sigue no se ejecuta.

## Estado

| Fase | Estado |
|---|---|
| Scanner | ✅ |
| Parser (sin AST) | ✅ |
| Semántico | ✅ |
| Código intermedio (TASM) | ✅ |
| Optimizador | ⏳ por definir |
| Código objeto (x86 16 bits) | ✅ (bytes verificados con tests, sin emulador) |

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
| CO | `POST /objeto` | tablas DATOS y CÓDIGO (DIR/CONTENIDO/HEX) |

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
  claro, porque la plantilla imprime 2 cifras. Si el valor viene de una
  variable no hay control en compilación: 100 o más se imprime mal

Si hiciera falta la pila (por ejemplo `a @ b & c` o `( a @ b )`), el botón CI
muestra un error claro en vez de generar código.

## Código objeto (CO)

El botón flotante **CO** abre un panel con dos tablas: **DATOS** (las variables)
y **CÓDIGO** (las instrucciones). Cada fila muestra `DIR | CONTENIDO | HEX`:

- `DIR` va en binario (16 bits en cuatro nibbles): `0010 0000 0000 0000`.
- `CONTENIDO` sale de los bytes reales, en nibbles: `1010 0001  0000 0010  0010 0000`.
- `HEX` son los mismos bytes en orden de memoria: `A1 02 20`.
- El tooltip de cada renglón dice la instrucción completa (`MOV AX,[2002h]`).

Convenciones: `DATA_BASE = 2000h` (2 bytes por variable, `00 00`),
`CODE_BASE = 0000h`, W = 1, little endian, complemento a 2. Las variables se
direccionan en forma directa (mod 00, r/m 110). El código termina en `HLT`; si
el programa tiene `print`, después va la rutina `rutina_print`, que imprime con
`DIV DL` + `INT 21H` / `AH=02H` igual que el CI y agrega `COC` y `RESI` (1 byte
cada una) a la tabla DATOS. Sin `print` no se emite la rutina.

`codificador.py` guarda las variantes en tablas (MOV, ADD/SUB/CMP, MUL/DIV,
saltos y pila) y arma el ModR/M. `objeto.py` recorre los tokens con la misma
forma que el parser y emite instrucciones. Los saltos se arman en dos pasadas:
si el relativo no entra en −128..127, se promueven a cercanos (`E9` o `0F 8x`).

Las comparaciones usan saltos **sin signo** (`>` → `JA`, `<` → `JB`): el
lenguaje maneja 0..65535 y `MUL`/`DIV` son sin signo, así que `40000 > 5` no
puede leerse como un negativo. `==` sigue siendo `JE`.

Ejemplo (`x` en 2000h, `y` en 2002h):

```text
x = y & 3;   → A1 02 20 · BB 03 00 · F7 E3 · A3 00 20
x = y | 3;   → A1 02 20 · BB 03 00 · BA 00 00 · F7 F3 · A3 00 20
```

Los bytes están verificados contra las tablas con tests unitarios. **No** se
verificó la ejecución: en esta máquina no hay DOSBox ni un emulador i8086.

## Decisiones técnicas

- **Sin AST.** El parser solo valida; el semántico y el generador copian su
  forma (mismo esqueleto, mismo orden). El precio es recorrer los tokens otra
  vez al generar; a cambio, no hay un árbol que mantener para un solo
  consumidor. Si el optimizador lo pide, se reabre la decisión.
- **Registros, no pila.** Todo se calcula en `AX` (un solo acumulador). Por eso
  solo se admiten operandos simples y operaciones del mismo nivel: si una
  expresión necesitara dos valores vivos a la vez, se muestra un error
  (`ErrorIntermedio`) en vez de generar código mal.
- **Los `bool` son `DB`** (1 byte, regla del profe): se cargan con `MOV AL` +
  `MOV AH, 0` y se comparan con `CMP AL`, así `AX` siempre vale 0 o 1 completo.
- **Las comparaciones son un valor.** `== > <` dejan 0/1 en `AX` con `SETcc` +
  `MOV AH, 0` (por eso existe `bool c = a == b`); en una condición se emite el
  salto negado (`<` → `JGE`).
- **El `print` usa la plantilla de 2 cifras** del handout (`DIV DL` parte el
  número: decenas en `COC`, unidades en `RESI`). Es correcto de 0 a 99; un
  literal fuera de rango se rechaza con un mensaje claro.
- **Los mensajes son fijos** (`Syntax OK`, `Semantic OK`,
  `Línea X: ERROR DE TIPOS: ...`): los tests los comparan exactos, así que no se
  reformulan.
- **El dominio va en castellano** (`tabla`, `linea`, `decl_var`); Flask, JS y
  TASM quedan en inglés porque es vocabulario técnico.
- **Sin dependencias de ejecución** más que Flask: `ruff`, `pyright` y `pytest`
  son de desarrollo (`requirements-dev.txt`).

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
backend/   tokens.py scanner.py parser.py semantico.py intermedio.py
           codificador.py objeto.py app.py
frontend/  index.html script.js style.css
tests/     test_smoke.py test_codificador.py test_objeto.py
docs/      gramatica.md errores.md
```
