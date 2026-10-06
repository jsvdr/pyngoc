import os
from typing import Any

# App: une scanner -> parser -> semántico -> intermedio y sirve la GUI.
# Lo de fuera no se confía: se revisa con isinstance o se devuelve 400.
from flask import Flask, Response, jsonify, request, send_from_directory
from intermedio import generar_codigo_intermedio
from parser import Parser
from scanner import analizar_lexico
from semantico import AnalizadorSemantico

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR: str = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__)

# Límite anti-DoS casero: rechaza POST gigantes con 413.
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


@app.route("/")
def index() -> Response:
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/style.css")
def style() -> Response:
    return send_from_directory(FRONTEND_DIR, "style.css")


@app.route("/script.js")
def script() -> Response:
    return send_from_directory(FRONTEND_DIR, "script.js")


# SCANNER
@app.route("/analizar", methods=["POST"])
def analizar() -> Response | tuple[Response, int]:
    # Viene del navegador y puede venir roto: si no es dict/str va 400.
    json_recibido: dict[str, Any] | None = request.get_json(silent=True)

    if not isinstance(json_recibido, dict):
        return jsonify(
            {
                "tokens": [],
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo_bruto: Any = json_recibido.get("codigo")

    if not isinstance(codigo_bruto, str):
        return jsonify(
            {
                "tokens": [],
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo_fuente: str = codigo_bruto

    lista_tokens, lista_errores = analizar_lexico(codigo_fuente)

    return jsonify(
        {
            "tokens": [str(token) for token in lista_tokens],
            "errores": lista_errores,
        }
    )


# PARSER
@app.route("/parser", methods=["POST"])
def analizar_parser() -> Response | tuple[Response, int]:
    # Viene del navegador y puede venir roto: si no es dict/str va 400.
    json_recibido: dict[str, Any] | None = request.get_json(silent=True)

    if not isinstance(json_recibido, dict):
        return jsonify(
            {
                "ok": False,
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo_bruto: Any = json_recibido.get("codigo")

    if not isinstance(codigo_bruto, str):
        return jsonify(
            {
                "ok": False,
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo_fuente: str = codigo_bruto

    lista_tokens, lista_errores_lexico = analizar_lexico(codigo_fuente)

    if lista_errores_lexico:
        return jsonify(
            {
                "ok": False,
                "errores": lista_errores_lexico,
            }
        )

    revisor_sintaxis = Parser(lista_tokens)

    es_valido, lista_errores = revisor_sintaxis.analizar()

    return jsonify(
        {
            "ok": es_valido,
            "errores": lista_errores,
        }
    )


# SEMÁNTICO
@app.route("/semantico", methods=["POST"])
def analizar_semantico() -> Response | tuple[Response, int]:
    # Viene del navegador y puede venir roto: si no es dict/str va 400.
    json_recibido: dict[str, Any] | None = request.get_json(silent=True)

    if not isinstance(json_recibido, dict):
        return jsonify(
            {
                "ok": False,
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo_bruto: Any = json_recibido.get("codigo")

    if not isinstance(codigo_bruto, str):
        return jsonify(
            {
                "ok": False,
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo_fuente: str = codigo_bruto

    # Scanner
    lista_tokens, lista_errores_lexico = analizar_lexico(codigo_fuente)

    if lista_errores_lexico:
        return jsonify(
            {
                "ok": False,
                "errores": lista_errores_lexico,
            }
        )

    # Parser
    revisor_sintaxis = Parser(lista_tokens)

    es_valido, lista_errores_sintaxis = revisor_sintaxis.analizar()

    if not es_valido:
        return jsonify(
            {
                "ok": False,
                "errores": lista_errores_sintaxis,
            }
        )

    # Semántico
    revisor_tipos = AnalizadorSemantico(lista_tokens)

    es_valido, lista_errores = revisor_tipos.analizar()

    return jsonify(
        {
            "ok": es_valido,
            "errores": lista_errores,
        }
    )


# CÓDIGO INTERMEDIO
@app.route("/intermedio", methods=["POST"])
def generar_intermedio() -> Response | tuple[Response, int]:
    # Viene del navegador y puede venir roto: si no es dict/str va 400.
    json_recibido: dict[str, Any] | None = request.get_json(silent=True)

    if not isinstance(json_recibido, dict):
        return jsonify(
            {
                "ok": False,
                "codigo": "",
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo_bruto: Any = json_recibido.get("codigo")

    if not isinstance(codigo_bruto, str):
        return jsonify(
            {
                "ok": False,
                "codigo": "",
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo_fuente: str = codigo_bruto

    # 1. Scanner
    lista_tokens, lista_errores_lexico = analizar_lexico(codigo_fuente)

    if lista_errores_lexico:
        return jsonify(
            {
                "ok": False,
                "codigo": "",
                "errores": lista_errores_lexico,
            }
        )

    # 2. Parser
    revisor_sintaxis = Parser(lista_tokens)

    es_valido, lista_errores_sintaxis = revisor_sintaxis.analizar()

    if not es_valido:
        return jsonify(
            {
                "ok": False,
                "codigo": "",
                "errores": lista_errores_sintaxis,
            }
        )

    # 3. Semántico
    revisor_tipos = AnalizadorSemantico(lista_tokens)

    es_valido, lista_errores_tipos = revisor_tipos.analizar()

    if not es_valido:
        return jsonify(
            {
                "ok": False,
                "codigo": "",
                "errores": lista_errores_tipos,
            }
        )

    # 4. Generar CI
    codigo_intermedio = generar_codigo_intermedio(revisor_tipos.tabla)

    return jsonify(
        {
            "ok": True,
            "codigo": codigo_intermedio,
            "errores": [],
        }
    )


if __name__ == "__main__":
    # Apagado por defecto: la consola Werkzeug no se expone.
    # Actívalo solo en desarrollo con FLASK_DEBUG=1.
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
