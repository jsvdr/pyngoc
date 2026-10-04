import os

from flask import Flask, jsonify, request, send_from_directory
from intermedio import generar_codigo_intermedio
from parser import Parser
from scanner import analizar_lexico
from semantico import AnalizadorSemantico

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__)

# Límite anti-DoS casero: rechaza POST gigantes con 413.
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/style.css")
def style():
    return send_from_directory(FRONTEND_DIR, "style.css")


@app.route("/script.js")
def script():
    return send_from_directory(FRONTEND_DIR, "script.js")


# SCANNER
@app.route("/analizar", methods=["POST"])
def analizar():
    data = request.get_json(silent=True)

    if not data or "codigo" not in data:
        return jsonify(
            {
                "tokens": [],
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo = data["codigo"]

    tokens, errores = analizar_lexico(codigo)

    return jsonify(
        {
            "tokens": [str(token) for token in tokens],
            "errores": errores,
        }
    )


# PARSER
@app.route("/parser", methods=["POST"])
def analizar_parser():
    data = request.get_json(silent=True)

    if not data or "codigo" not in data:
        return jsonify(
            {
                "ok": False,
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo = data["codigo"]

    tokens, errores_lexicos = analizar_lexico(codigo)

    if errores_lexicos:
        return jsonify(
            {
                "ok": False,
                "errores": errores_lexicos,
            }
        )

    parser = Parser(tokens)

    ok, errores = parser.analizar()

    return jsonify(
        {
            "ok": ok,
            "errores": errores,
        }
    )


# SEMÁNTICO
@app.route("/semantico", methods=["POST"])
def analizar_semantico():
    data = request.get_json(silent=True)

    if not data or "codigo" not in data:
        return jsonify(
            {
                "ok": False,
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo = data["codigo"]

    # Scanner
    tokens, errores_lexicos = analizar_lexico(codigo)

    if errores_lexicos:
        return jsonify(
            {
                "ok": False,
                "errores": errores_lexicos,
            }
        )

    # Parser
    parser = Parser(tokens)

    ok, errores_sintacticos = parser.analizar()

    if not ok:
        return jsonify(
            {
                "ok": False,
                "errores": errores_sintacticos,
            }
        )

    # Semántico
    semantico = AnalizadorSemantico(tokens)

    ok, errores = semantico.analizar()

    return jsonify(
        {
            "ok": ok,
            "errores": errores,
        }
    )


# CÓDIGO INTERMEDIO
@app.route("/intermedio", methods=["POST"])
def generar_intermedio():
    data = request.get_json(silent=True)

    if not data or "codigo" not in data:
        return jsonify(
            {
                "ok": False,
                "codigo": "",
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo = data["codigo"]

    # 1. Scanner
    tokens, errores_lexicos = analizar_lexico(codigo)

    if errores_lexicos:
        return jsonify(
            {
                "ok": False,
                "codigo": "",
                "errores": errores_lexicos,
            }
        )

    # 2. Parser
    parser = Parser(tokens)

    ok, errores_sintacticos = parser.analizar()

    if not ok:
        return jsonify(
            {
                "ok": False,
                "codigo": "",
                "errores": errores_sintacticos,
            }
        )

    # 3. Semántico
    semantico = AnalizadorSemantico(tokens)

    ok, errores_semanticos = semantico.analizar()

    if not ok:
        return jsonify(
            {
                "ok": False,
                "codigo": "",
                "errores": errores_semanticos,
            }
        )

    # 4. Generar CI
    codigo_intermedio = generar_codigo_intermedio(semantico.tabla)

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
