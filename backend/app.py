import os
from collections.abc import Mapping
from typing import cast

# App: une scanner -> parser -> semántico -> intermedio y sirve la GUI.
# Lo de fuera no se confía: se revisa con isinstance o se devuelve 400.
from flask import Flask, Response, jsonify, request
from intermedio import ErrorIntermedio, generar_codigo_intermedio
from objeto import generar_codigo_objeto
from parser import Parser
from scanner import analizar_lexico
from semantico import AnalizadorSemantico
from tokens import Token

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR: str = os.path.join(BASE_DIR, "frontend")

# static_url_path="" sirve index.html, style.css y script.js sin tres rutas.
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

# Límite anti-DoS casero: rechaza POST gigantes con 413.
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

CODIGO_FALTANTE = "No se recibió código para analizar."


@app.route("/")
def index() -> Response:
    return app.send_static_file("index.html")


# Viene del navegador y puede venir roto: None si no hay código de texto.
def leer_codigo() -> str | None:
    datos: object = request.get_json(silent=True)

    if not isinstance(datos, Mapping):
        return None

    codigo = cast(Mapping[str, object], datos).get("codigo")

    if isinstance(codigo, str):
        return codigo

    return None


# Scanner + parser. Si una fase falla, la siguiente no se corre.
def revisar_hasta_sintaxis(codigo: str) -> tuple[bool, list[str], list[Token]]:
    tokens, errores = analizar_lexico(codigo)

    if errores:
        return False, errores, tokens

    es_valido, errores = Parser(tokens).analizar()

    return es_valido, errores, tokens


# Scanner + parser + semántico. Devuelve también la tabla de tipos.
def revisar_hasta_semantico(
    codigo: str,
) -> tuple[bool, list[str], list[Token], dict[str, str]]:
    es_valido, errores, tokens = revisar_hasta_sintaxis(codigo)

    if not es_valido:
        return False, errores, tokens, {}

    revisor_tipos = AnalizadorSemantico(tokens)

    es_valido, errores = revisor_tipos.analizar()

    return es_valido, errores, tokens, revisor_tipos.tabla


# SCANNER
@app.route("/analizar", methods=["POST"])
def analizar() -> Response | tuple[Response, int]:
    codigo = leer_codigo()

    if codigo is None:
        return jsonify({"tokens": [], "errores": [CODIGO_FALTANTE]}), 400

    lista_tokens, lista_errores = analizar_lexico(codigo)

    return jsonify(
        {
            "tokens": [str(token) for token in lista_tokens],
            "errores": lista_errores,
        }
    )


# PARSER
@app.route("/parser", methods=["POST"])
def analizar_parser() -> Response | tuple[Response, int]:
    codigo = leer_codigo()

    if codigo is None:
        return jsonify({"ok": False, "errores": [CODIGO_FALTANTE]}), 400

    es_valido, errores, _ = revisar_hasta_sintaxis(codigo)

    return jsonify({"ok": es_valido, "errores": errores})


# SEMÁNTICO
@app.route("/semantico", methods=["POST"])
def analizar_semantico() -> Response | tuple[Response, int]:
    codigo = leer_codigo()

    if codigo is None:
        return jsonify({"ok": False, "errores": [CODIGO_FALTANTE]}), 400

    es_valido, errores, _, _ = revisar_hasta_semantico(codigo)

    return jsonify({"ok": es_valido, "errores": errores})


# CÓDIGO INTERMEDIO
@app.route("/intermedio", methods=["POST"])
def generar_intermedio() -> Response | tuple[Response, int]:
    codigo = leer_codigo()

    if codigo is None:
        return respuesta_sin_intermedio([CODIGO_FALTANTE]), 400

    es_valido, errores, lista_tokens, tabla = revisar_hasta_semantico(codigo)

    if not es_valido:
        return respuesta_sin_intermedio(errores)

    try:
        filas = generar_codigo_intermedio(tabla, lista_tokens)
    except ErrorIntermedio as error:
        return respuesta_sin_intermedio([str(error)])

    mensaje = ""
    if len(filas) == 0:
        mensaje = "No hay variables para generar."

    return jsonify(
        {
            "ok": True,
            "filas": filas,
            "mensaje": mensaje,
            "errores": [],
        }
    )


# CÓDIGO OBJETO
@app.route("/objeto", methods=["POST"])
def generar_objeto() -> Response | tuple[Response, int]:
    codigo = leer_codigo()

    if codigo is None:
        return respuesta_sin_objeto([CODIGO_FALTANTE]), 400

    es_valido, errores, lista_tokens, tabla = revisar_hasta_semantico(codigo)

    if not es_valido:
        return respuesta_sin_objeto(errores)

    es_valido, datos, codigo_objeto, errores = generar_codigo_objeto(
        lista_tokens,
        tabla,
    )

    if not es_valido:
        return respuesta_sin_objeto(errores)

    return jsonify(
        {
            "ok": True,
            "datos": datos,
            "codigo": codigo_objeto,
            "errores": [],
        }
    )


def respuesta_sin_intermedio(lista_errores: list[str]) -> Response:
    return jsonify(
        {
            "ok": False,
            "filas": [],
            "mensaje": "",
            "errores": lista_errores,
        }
    )


# El panel tiene que avisar que no se puede generar y mostrar por qué.
# Los errores concretos van primero para que se lean; el aviso, al final.
def respuesta_sin_objeto(lista_errores: list[str]) -> Response:
    return jsonify(
        {
            "ok": False,
            "datos": [],
            "codigo": [],
            "errores": [
                *lista_errores,
                "No se puede generar código objeto.",
            ],
        }
    )


if __name__ == "__main__":
    # Puerto por entorno para nube/local sin tocar código. Por defecto 5000.
    PORT: int = int(os.getenv("PORT", "5000"))
    # Apagado por defecto: la consola Werkzeug no se expone.
    # Actívalo solo en desarrollo con FLASK_DEBUG=1.
    app.run(
        host="127.0.0.1",
        port=PORT,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
