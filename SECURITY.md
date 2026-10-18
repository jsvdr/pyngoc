# Política de seguridad

Proyecto didáctico (compilador Pyngo). Sin datos de usuarios,
sin secretos y sin despliegue productivo.

## Reportar una vulnerabilidad

Abre un Issue privado en este repositorio describiendo el problema
y cómo reproducirlo. Responderemos en un máximo de 90 días.

## Alcance

- `backend/app.py` (superficie HTTP local: `127.0.0.1:5000`)
- Dependencias fijadas en `requirements.txt`

El resto (`scanner.py`, `parser.py`, `semantico.py`, `frontend/`)
no procesa entrada de red directamente.

## Qué puede salir mal (modelado rápido)

- **Entrada del usuario:** el texto pegado se procesa en el servidor. Está
  acotado a 64 KB (`MAX_CONTENT_LENGTH`), pero un programa muy anidado puede
  agotar la recursión de Python y devolver un 500. Nunca se ejecuta código.
- **Modo debug:** `FLASK_DEBUG=1` activa el debugger de Flask, que permite
  ejecutar código desde el navegador. Por eso la app escucha solo en
  `127.0.0.1` y el debug está apagado por defecto. No exponerla en red.
- **Inyección:** el frontend pinta todo con `textContent`, nunca con
  `innerHTML`, así que el código del usuario no puede inyectar HTML.
- **Datos:** no hay base de datos, ni sesiones, ni autenticación. No hay
  nada que filtrar ni que perder.
