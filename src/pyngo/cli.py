"""Command-line interface for Pyngo."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .codegen import PanelRow, generate_object_code
from .ir import IRError, generate_ir
from .lexer import tokenize
from .parser import Parser
from .semantic import SemanticAnalyzer
from .tokens import Token


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_front_end(source: str) -> tuple[bool, list[str], list[Token], dict[str, str]]:
    tokens, lexer_errors = tokenize(source)
    if lexer_errors:
        return False, lexer_errors, tokens, {}

    is_valid, parser_errors = Parser(tokens).analyze()
    if not is_valid:
        return False, parser_errors, tokens, {}

    analyzer = SemanticAnalyzer(tokens)
    is_valid, semantic_errors = analyzer.analyze()
    return is_valid, semantic_errors, tokens, analyzer.symbol_table


def print_errors(errors: list[str]) -> None:
    for error in errors:
        print(error, file=sys.stderr)


def print_ir(rows: list[tuple[str, str, str]]) -> None:
    print("IR")
    print(f"{'NAME':<12}{'OPERATOR':<10}ATTRIBUTE")
    for name, operator, attribute in rows:
        print(f"{name:<12}{operator:<10}{attribute}")


def print_object_code(
    data: list[PanelRow],
    code: list[PanelRow],
) -> None:
    print("OBJECT CODE")
    print("DATA")
    print(f"{'ADDRESS':<20}{'HEX':<8}TEXT")
    for row in data:
        print(f"{row['address']:<20}{row['hex']:<8}{row['text']}")

    print("CODE")
    print(f"{'ADDRESS':<20}{'HEX':<20}TEXT")
    for row in code:
        print(f"{row['address']:<20}{row['hex']:<20}{row['text']}")


def build(path: Path, as_json: bool = False) -> int:
    source = read_source(path)

    is_valid, errors, tokens, symbol_table = run_front_end(source)
    if not is_valid:
        return report_errors(errors, as_json)

    try:
        ir_rows = generate_ir(symbol_table, tokens)
    except IRError as error:
        return report_errors([str(error)], as_json)

    is_valid, data, code, errors = generate_object_code(tokens, symbol_table)
    if not is_valid:
        return report_errors(errors, as_json)

    if as_json:
        print(json.dumps({"ok": True, "data": data, "code": code, "errors": []}))
        return 0

    print("Syntax OK")
    print("Semantic OK")
    print_ir(ir_rows)
    print_object_code(data, code)
    return 0


# In JSON mode the caller (pyngo-run, a script) reads one object, never prose.
def report_errors(errors: list[str], as_json: bool) -> int:
    if as_json:
        print(json.dumps({"ok": False, "data": [], "code": [], "errors": errors}))
    else:
        print_errors(errors)
    return 1


def check(path: Path) -> int:
    source = read_source(path)

    is_valid, errors, _, _ = run_front_end(source)
    if not is_valid:
        print_errors(errors)
        return 1

    print("Syntax OK")
    print("Semantic OK")
    return 0


def serve(host: str, port: int, debug: bool) -> int:
    from .app import app

    app.run(host=host, port=port, debug=debug)
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyngo", description="A small multi-phase compiler.")
    _ = parser.add_argument("--version", action="version", version=f"pyngo {__version__}")

    commands = parser.add_subparsers(dest="command", required=True)

    build_parser = commands.add_parser("build", help="compile a .pyn file and print IR + object code")
    _ = build_parser.add_argument("file", type=Path)
    _ = build_parser.add_argument(
        "--json",
        action="store_true",
        help="print one JSON object (data + code) instead of the readable report",
    )

    check_parser = commands.add_parser("check", help="run lexer, parser and semantic checks")
    _ = check_parser.add_argument("file", type=Path)

    serve_parser = commands.add_parser("serve", help="start the development web server")
    _ = serve_parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    _ = serve_parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "5000")))
    _ = serve_parser.add_argument("--debug", action="store_true", default=os.getenv("FLASK_DEBUG") == "1")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)

    if args.command == "build":
        return build(args.file, args.json)
    if args.command == "check":
        return check(args.file)
    if args.command == "serve":
        return serve(args.host, args.port, args.debug)

    parser.error(f"unknown command: {args.command}")
    return 2
