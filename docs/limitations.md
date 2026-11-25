# Limitations

Pyngo is a didactic compiler, not a production language. This is the complete
list of what it does **not** do, with the reason and the workaround.

## Language

| Limitation | Detail | Workaround |
|---|---|---|
| No `else` | `if` has no alternative branch | negate the condition in a second `if` |
| `print` only takes a variable | `print ( 42 )` is a syntax error (`PRINT → print ( ID )`) | assign to a variable first |
| `print` shows two digits | the routine divides by 10 and prints the quotient and the remainder | values `0..99` print correctly; above that the output is not defined |
| `int` is `0..65535` | unsigned only; literals above `65535` are a type error | stay below `65536` |
| No negative numbers | `0 # 1` wraps to `65535` | keep subtractions positive |
| No comments | `//` and `/* */` are invalid characters | none |
| No strings, arrays, functions, `for` | not in the grammar | use `int`/`bool` and `while` |
| Identifiers are ASCII lowercase | `[a-z][a-z0-9]*`; `A`, `ñ`, `²` are lexer errors | use lowercase names |
| Division by zero | not detected at compile time | the generated code faults at run time |
| `MUL` overflow | the 16-bit result wraps around silently | keep products below `65536` |
| No block without braces | `if x > 0 a = 1;` is a syntax error | always write `{ … }` |

## Intermediate code

`ir.py` is the simple back end: every expression is computed in `AX` and only
a **simple** right-hand operand is accepted (a variable, a number or
`true`/`false`). Programs that need two live values — `a & (b @ c)`,
`if (a @ 1) > 2` — make the IR panel report an error such as *"The right-hand
side of the addition or subtraction must be a simple operand."*

The object-code phase handles those programs correctly (it uses the stack),
so the limitation belongs to the IR view, not to the compiler as a whole.

## Compiler

- **No optimizer.** There is no constant folding, no dead-code removal and no
  register allocation. `i = i @ 1` reloads `i` from memory every time.
- **No AST.** Each phase walks the tokens again (see
  [ADR 0001](adr/0001-no-ast.md)).
- **Deep nesting** (`((((((…))))))`) can exhaust Python's recursion limit and
  return HTTP 500 from the web app.
- **Only x86-16.** The object code targets real-mode DOS style (`INT 21H`,
  `MOV AH, 02H`); there is no ELF/PE executable writer, no linker and no
  `.COM` header.
- **No floating point**, no type coercion: `int` and `bool` never mix.

## Deployment

- The public demo runs on a free Render instance: it sleeps after inactivity
  and needs 30–50 s to answer the first request.
- The Flask development server is the local default; production uses
  `gunicorn` (see the `Dockerfile` and `render.yaml`).
