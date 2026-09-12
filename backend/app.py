import os

from flask import Flask, jsonify, request, send_from_directory
from scanner import analizar_lexico

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
            {
                "tokens": [],
                "errores": ["No se recibió código para analizar."],
            }
        ), 400

    codigo = data["codigo"]

    tokens, errores = analizar_lexico(codigo)

    return jsonify(
        {
            "tokens": tokens,
            "errores": errores,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
