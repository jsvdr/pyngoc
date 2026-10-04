# Sesión nueva — contexto Pyngo (léeme primero)

Compilador didáctico por fases, código para tontos. Examen pasado (90,
pide pseudocódigo). Reglas de estilo en `AGENTS.md`: español de dominio,
sin AST, mensajes exactos, gramática intocable sin permiso.

## Estado por fases

- ✅ Scanner (`scanner.py`): texto → tokens, junta todos los errores.
- ✅ Parser (`parser.py`): solo reconoce, sin nodos ni `arbol.py`.
- ✅ Semántico (`semantico.py`): copia del parser + `tabla = {}`
  (el HashMap); devuelve `"int"`/`"bool"`, `None` = error previo.
- ✅ Intermedio (`intermedio.py` + ruta `/intermedio`): tabla → `DW/DB ?`.
- ⏳ Optimizador: pendiente (alcance por definir con el profe).
- ⏳ Código máquina: noviembre (destino por definir).

## Decisiones blindadas (no reabrir sin pedir)

- `tabla[nombre] = tipo` se guarda incluso con error de tipos;
  `return` temprano solo ante redeclaración (evita errores en cascada).
- `linea = actual().line` se captura ANTES de consumir la expresión.
- Operadores `@ # & |` exigidos por el profe; `{}`, `;` obligatorios.
- Duplicación `decl_var`/`asignacion` intencional (cada método se lee solo).
- Frontend: 3 paneles + CI abajo-izquierda 50%, sin botón Limpiar,
  éxito verde `#1e7d32`, fuentes proyector (código 20px, UI 18px).

## Comandos

```bash
python backend/app.py        # :5000
pytest tests/ -q             # 5 humo, siempre verdes
ruff check backend/ tests/ && ruff format --check backend/ tests/
```

## 5 casos que siempre funcionan

```text
{ int a = 1; bool b = true; }   → Semantic OK
{ int x = true; }               → ERROR DE TIPOS (es int, recibió bool)
{ x = 10; }                     → ERROR DE DECLARACIÓN (no declarada)
{ int x = 1; int x = 2; }       → ERROR DE DECLARACIÓN (ya declarada)
CI de { int c = 1; ... }        → contador DW ? / limite DW ? / activo DB ?
```

## Pseudocódigo de 7 líneas (el del examen)

```text
¿ya existe? → error + return (no sobrescribe)
¿tipos iguales? → error si difieren
guardar en tabla (siempre, aun con error de tipos)
```

## Git

`main` en `github.com/jsvdr/pyngoc` (privado hasta nov).
`.github/workflows/` no se sube por push (token sin alcance
`workflow`): va por web + `git pull`. Commits en español `feat:/fix:/ci:`.
