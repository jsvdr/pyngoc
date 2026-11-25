# Pyngo grammar

Each rule is a method with the same name in `parser.py`
and `semantic.py`.

```text
PROGRAM     → { DECL_LIST }
DECL_LIST   → [ DECL ; ]*

DECL        → VAR_DECL | ASSIGNMENT | IF | WHILE | PRINT

VAR_DECL    → DATA_TYPE ID = EXPRESSION
ASSIGNMENT  → ID = EXPRESSION

IF          → if EXPRESSION { DECL_LIST }
WHILE       → while EXPRESSION { DECL_LIST }
PRINT       → print ( ID )

DATA_TYPE   → int | bool

EXPRESSION  → SUM [ ( == | > | < ) SUM ]
SUM         → TERM [ ( @ | # ) TERM ]*
TERM        → FACTOR [ ( & | | ) FACTOR ]*
FACTOR      → ID | NUM | BOOL | ( EXPRESSION )

BOOL        → true | false
ID          → [a-z] [a-z0-9]*   (ASCII only: no uppercase, no 'ñ')
```

## Semantic rules (not in the grammar; we define them)

```text
@ # & |  →  int, int → int
==       →  same type → bool
> <      →  int, int → bool
if/while →  the condition must be bool
print    →  the variable must be int
```
