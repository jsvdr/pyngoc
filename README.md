# Pyngo — compilador didáctico

Compilador por fases (scanner → parser → semántico → código intermedio)
para un lenguaje propio con `int`/`bool`, `if`/`for`/`print` y operadores
`@ # & | == > <`. Backend en Flask, frontend vanilla, sin dependencias de más.

## Cómo correrlo

```bash
pip install -r requirements.txt
python backend/app.py
```

Abre `http://127.0.0.1:5000`. Desarrollo con recarga: `FLASK_DEBUG=1`.

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
backend/   scanner.py parser.py semantico.py intermedio.py app.py
frontend/  index.html script.js style.css
```
