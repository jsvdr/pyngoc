# Error detection (pseudocode = the real code, compressed)

The semantic analyzer copies the parser's shape, but each method returns
the type (`"int"` / `"bool"`) instead of only consuming tokens. Empty text
(`None`) = unknown type because of an earlier error, so it does not produce
more errors.

## Declaration (`var_decl`)

```python
if name in symbol_table:
    error "has already been declared"
    return                      # do not overwrite
if expression_type is not None and variable_type != expression_type:
    error "TYPE: is {variable_type}, but got {expression_type}"
symbol_table[name] = variable_type   # always, even after a type error
```

## Assignment (`assignment`) — mirror of the previous one

```python
if name not in symbol_table:
    error "has not been declared"
    return
if expression_type is not None and variable_type != expression_type:
    error "TYPE: is {variable_type}, but was assigned {expression_type}"
```

Differences from declaration: `in` → `not in`, `declared` → `undeclared`,
`got` → `assigned`, and there is no final store.

## Operators (`expression` / `sum` / `term` / `factor`)

```python
type(ID x):
    if x not in symbol_table: error "DECLARATION", return None
    return symbol_table[x]
type(op, left, right):
    left_type, right_type = type(left), type(right)
    if either is None: return None
    @ # & | require int → int
    == requires equal types → bool
    > < require int → bool
    if invalid: error "TYPE" on the operator's line, return None
```

## Correct line

```python
line = current().line  # BEFORE consuming the expression
```

If it were reported after `expression()`, it would point at the `;`.
