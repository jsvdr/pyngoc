# Detección de errores (pseudocódigo = código real compactado)

El semántico copia la forma del parser, pero cada método devuelve
el tipo (`"int"` / `"bool"`) en vez de solo consumir. Texto vacío
(`None`) = tipo desconocido por un error previo, no genera más errores.

## Declaración (`decl_var`)

```python
if nombre in tabla:
    error "ya fue declarada"
    return                      # no sobrescribe
if tipo_expr is not None and tipo_var != tipo_expr:
    error "TIPOS: es {tipo_var}, pero se recibió {tipo_expr}"
tabla[nombre] = tipo_var         # siempre, aun con error de tipos
```

## Asignación (`asignacion`) — espejo del anterior

```python
if nombre not in tabla:
    error "no ha sido declarada"
    return
if tipo_expr is not None and tipo_var != tipo_expr:
    error "TIPOS: es {tipo_var}, pero se asignó {tipo_expr}"
```

Diferencias con declaración: `in` → `not in`, `YA` → `NO`,
`recibió` → `asignó`, y no hay guardado final.

## Operadores (`expresion` / `suma` / `termino` / `factor`)

```python
tipo(ID x):
    si x no en tabla: error "DECLARACIÓN", return None
    return tabla[x]
tipo(op, izq, der):
    ti, td = tipo(izq), tipo(der)
    si alguno es None: return None
    @ # & | exigen int → int
    == exige iguales → bool
    > < exigen int → bool
    si no cumple: error "TIPOS" con la línea del operador, return None
```

## Línea correcta

```python
linea = actual().line   # ANTES de consumir la expresión
```

Si se reportara después de `expresion()`, apuntaría al `;`.
