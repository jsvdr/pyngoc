import os

from flask import Flask, jsonify, request, send_from_directory
from parser import Parser
from scanner import analizar_lexico
from semantico import AnalizadorSemantico

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__)


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
    data = request.get_json()

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
    data = request.get_json()

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
    data = request.get_json()

    if not data or "codigo" not in data:
        return jsonify(
            {
                "ok": False,
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo = data["codigo"]

    # Primero: scanner
    tokens, errores_lexicos = analizar_lexico(codigo)

    if errores_lexicos:
        return jsonify(
            {
                "ok": False,
                "errores": errores_lexicos,
            }
        )

    # Segundo: parser
    parser = Parser(tokens)

    ok, errores_sintacticos = parser.analizar()

    if not ok:
        return jsonify(
            {
                "ok": False,
                "errores": errores_sintacticos,
            }
        )

    # Tercero: semántico
    semantico = AnalizadorSemantico(tokens)

    ok, errores = semantico.analizar()

    return jsonify(
        {
            "ok": ok,
            "errores": errores,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
