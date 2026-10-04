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
