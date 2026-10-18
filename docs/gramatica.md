# Gramática de Pyngo

Cada regla es un método con el mismo nombre en `parser.py`
y en `semantico.py`.

```text
PROGRAMA    → { LISTA_DECL }
LISTA_DECL  → [ DECL ; ]*

DECL        → DECL_VAR | ASIGNACION | IF | WHILE | PRINT

DECL_VAR    → TIPO_DATO ID = EXPRESION
ASIGNACION  → ID = EXPRESION

IF          → if EXPRESION { LISTA_DECL } [ else { LISTA_DECL } ]
WHILE       → while EXPRESION { LISTA_DECL }
PRINT       → print ( EXPRESION )

TIPO_DATO   → int | bool

EXPRESION   → SUMA [ ( == | > | < ) SUMA ]
SUMA        → TERMINO [ ( @ | # ) TERMINO ]*
TERMINO     → FACTOR [ ( & | | ) FACTOR ]*
FACTOR      → ID | NUM | BOOL | ( EXPRESION )

BOOL        → true | false
ID          → [a-z] [a-z0-9]*   (solo ASCII: sin mayúsculas ni 'ñ')
```

## Reglas semánticas (no están en la gramática, las definimos nosotros)

```text
@ # & |  →  int, int → int
==       →  mismo tipo → bool
> <      →  int, int → bool
if/while →  la condición debe ser bool
```
