import os

from flask import Flask, jsonify, request, send_from_directory
from parser import Parser
from scanner import Scanner

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


@app.route("/analizar", methods=["POST"])
def analizar():
    data = request.get_json()

    if not data or "codigo" not in data:
        return jsonify(
            {"tokens": [], "errores": ["No se recibió código para analizar."]}
        ), 400

    codigo = data["codigo"]

    scanner = Scanner(codigo)
    tokens, errores = scanner.analizar()

    return jsonify({"tokens": [str(token) for token in tokens], "errores": errores})


@app.route("/parser", methods=["POST"])
def ejecutar_parser():
    data = request.get_json()

    if not data or "codigo" not in data:
        return jsonify(
            {
                "resultado": "Syntax Error",
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo = data["codigo"]

    scanner = Scanner(codigo)
    tokens, errores_scanner = scanner.analizar()

    if errores_scanner:
        return jsonify({"resultado": "Syntax Error", "errores": errores_scanner})

    parser = Parser(tokens)
    correcto, errores_parser = parser.analizar()

    if correcto:
        return jsonify({"resultado": "Syntax OK", "errores": []})

    return jsonify({"resultado": "Syntax Error", "errores": errores_parser})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
