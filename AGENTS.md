# AGENTS.md — Pyngo

Compilador didáctico por fases. Código para tontos: simple de leer
y explicar, aunque parezca menos "profesional". La simplicidad manda
sobre DRY y sobre ceremonia.

## Stack y comandos

- Backend: Python 3.12 + Flask (`pip install -r requirements.txt`).
- Servidor: `python backend/app.py` → `http://127.0.0.1:5000`.
- Lint/formato: `ruff check backend/ tests/` y `ruff format --check backend/ tests/`.
- Tests: `pytest tests/ -q` (22 casos de humo, deben pasar siempre).
- Frontend: HTML/CSS/JS vanilla servido por Flask. Puertos: Flask `:5000`.

## Convenciones (no negociables sin preguntar)

- Identificadores de dominio en español (`tabla`, `linea`, `decl_var`).
  `Token(kind, lexeme, line)`, Flask y JS quedan en inglés: es vocabulario
  técnico, no se renombra.
- Sin AST: el parser solo reconoce (sin `return Nodo...`, sin `arbol.py`).
  El semántico copia la forma del parser y devuelve tipos (`"int"`/`"bool"`,
  `None` = desconocido por error previo).
- Duplicación `decl_var`/`asignacion` intencional: cada método se lee solo
  y calca su producción. No extraer helpers sin pedirlo.
- Mensajes fijos: `Syntax OK`, `Semantic OK`,
  `Línea X: ERROR DE TIPOS: ...`, `Línea X: ERROR DE DECLARACIÓN: ...`.
  Los tests los comparan exactos.
- Gramática con `@ # & |` (exigidos por el profesor) y `{}`, `;`.
  No cambiar operadores ni producciones sin confirmación explícita.
- `tabla[nombre] = tipo` se guarda incluso con error de tipos;
  `return` temprano solo ante redeclaración. `linea` se captura ANTES
  de consumir la expresión. No "optimizar" esto: evita errores en cascada.
- GUI: 3 paneles fijos + panel CI abajo-izquierda al 50%. Cada fase limpia
  sus salidas sola (no existe botón Limpiar). Éxito en verde `#1e7d32`,
  error en rojo, fuentes modo proyector (código 20px, UI 18px).

## Guardarraíles

- `.github/workflows/` sí se puede pushear: el token tiene alcance `workflow`.
  Si algún día falla por eso, ese cambio va por la web de GitHub + `git pull`.
- No agregar dependencias, frameworks, type hints globales, docstrings
  obligatorias ni empaquetado `src/` sin pedirlo antes.
- Commits en español, estilo `feat:`/`fix:`/`ci:`.

## Verificación y entrega

- No digas que algo funciona ni que las pruebas pasan si no ejecutaste el
  comando. Muestra el comando y su salida real.
- Si algo no se puede verificar (falta un ensamblador, falta `dosbox`),
  dilo explícito. "Debería andar" no es "anda".
- No debilites ni borres pruebas, ni silencies errores, para que pase el CI.
- No uses `push --force` ni `reset --hard` sin autorización.
- El código tiene que quedar explicable en el examen: ante dos soluciones,
  elegí la que se pueda defender en voz alta.
- Al terminar, reportá: qué cambió, qué archivos, qué comandos corriste,
  qué pasó y qué queda pendiente.

## Material local (no versionado)

Si existe `plantillas-pyngo/`, es material de trabajo local: plantillas del
profesor (`plantillas.md`, `ejemplos/`) y notas propias (`sesion.md`). Leer
`plantillas.md` antes de tocar `backend/intermedio.py`. Esa carpeta está
ignorada vía `.git/info/exclude`: no se sube nunca, no agregarla a git ni
citar su contenido en el repo.
