import os
from collections.abc import Mapping
from pathlib import Path
from typing import cast

# App: wires lexer -> parser -> semantic -> IR and serves the GUI.
# Anything from outside is untrusted: check it with isinstance or return 400.
from flask import Flask, Response, jsonify, request

from .codegen import generate_object_code
from .ir import IRError, generate_ir
from .lexer import tokenize
from .parser import Parser
from .semantic import SemanticAnalyzer
from .tokens import Token

BASE_DIR: Path = Path(__file__).resolve().parents[2]
web_dir: Path = BASE_DIR / "web"
if not web_dir.is_dir():  # installed wheel: static files live next to app.py
    web_dir = Path(__file__).resolve().parent / "web"

# static_url_path="" serves index.html, style.css and script.js without three routes.
app = Flask(__name__, static_folder=str(web_dir), static_url_path="")

# Homemade anti-DoS limit: reject giant POST bodies with 413.
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

MISSING_CODE = "No code was provided for analysis."


@app.route("/")
def index() -> Response:
    return app.send_static_file("index.html")


@app.route("/healthz")
def healthz() -> Response:
    return jsonify({"status": "ok"})


# It comes from the browser and may be broken: None if there is no source text.
def read_source() -> str | None:
    data: object = request.get_json(silent=True)

    if not isinstance(data, Mapping):
        return None

    source = cast(Mapping[str, object], data).get("source")

    if isinstance(source, str):
        return source

    return None


# Lexer + parser. If one phase fails, the next one does not run.
def check_syntax(source: str) -> tuple[bool, list[str], list[Token]]:
    tokens, errors = tokenize(source)

    if errors:
        return False, errors, tokens

    is_valid, errors = Parser(tokens).analyze()

    return is_valid, errors, tokens


# Lexer + parser + semantic. Also returns the type table.
def check_semantic(
    source: str,
) -> tuple[bool, list[str], list[Token], dict[str, str]]:
    is_valid, errors, tokens = check_syntax(source)

    if not is_valid:
        return False, errors, tokens, {}

    type_checker = SemanticAnalyzer(tokens)

    is_valid, errors = type_checker.analyze()

    return is_valid, errors, tokens, type_checker.symbol_table


# LEXER
@app.route("/tokens", methods=["POST"])
def tokens_endpoint() -> Response | tuple[Response, int]:
    source = read_source()

    if source is None:
        return jsonify({"tokens": [], "errors": [MISSING_CODE]}), 400

    token_list, error_list = tokenize(source)

    return jsonify(
        {
            "tokens": [str(token) for token in token_list],
            "errors": error_list,
        }
    )


# PARSER
@app.route("/parser", methods=["POST"])
def parser_endpoint() -> Response | tuple[Response, int]:
    source = read_source()

    if source is None:
        return jsonify({"ok": False, "errors": [MISSING_CODE]}), 400

    is_valid, errors, _ = check_syntax(source)

    return jsonify({"ok": is_valid, "errors": errors})


# SEMANTIC
@app.route("/semantic", methods=["POST"])
def semantic_endpoint() -> Response | tuple[Response, int]:
    source = read_source()

    if source is None:
        return jsonify({"ok": False, "errors": [MISSING_CODE]}), 400

    is_valid, errors, _, _ = check_semantic(source)

    return jsonify({"ok": is_valid, "errors": errors})


# INTERMEDIATE CODE
@app.route("/ir", methods=["POST"])
def ir_endpoint() -> Response | tuple[Response, int]:
    source = read_source()

    if source is None:
        return no_ir_response([MISSING_CODE]), 400

    is_valid, errors, token_list, symbol_table = check_semantic(source)

    if not is_valid:
        return no_ir_response(errors)

    try:
        rows = generate_ir(symbol_table, token_list)
    except IRError as error:
        return no_ir_response([str(error)])

    message = ""
    if len(rows) == 0:
        message = "No variables to generate."

    return jsonify(
        {
            "ok": True,
            "rows": rows,
            "message": message,
            "errors": [],
        }
    )


# OBJECT CODE
@app.route("/object", methods=["POST"])
def object_endpoint() -> Response | tuple[Response, int]:
    source = read_source()

    if source is None:
        return no_object_response([MISSING_CODE]), 400

    is_valid, errors, token_list, symbol_table = check_semantic(source)

    if not is_valid:
        return no_object_response(errors)

    is_valid, data, object_code, errors = generate_object_code(
        token_list,
        symbol_table,
    )

    if not is_valid:
        return no_object_response(errors)

    return jsonify(
        {
            "ok": True,
            "data": data,
            "code": object_code,
            "errors": [],
        }
    )


def no_ir_response(error_list: list[str]) -> Response:
    return jsonify(
        {
            "ok": False,
            "rows": [],
            "message": "",
            "errors": error_list,
        }
    )


# The panel must say that generation is impossible and show why.
# Concrete errors come first so they are read first; the notice goes last.
def no_object_response(error_list: list[str]) -> Response:
    return jsonify(
        {
            "ok": False,
            "data": [],
            "code": [],
            "errors": [
                *error_list,
                "Cannot generate object code.",
            ],
        }
    )


if __name__ == "__main__":
    # Port from the environment for cloud/local without touching code. Defaults to 5000.
    PORT: int = int(os.getenv("PORT", "5000"))
    # Off by default: the Werkzeug console is not exposed.
    # Enable it only in development with FLASK_DEBUG=1.
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=PORT,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
