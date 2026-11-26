"""Atheris target: arbitrary text through every phase and into the emulator.

The contract is that no input makes the compiler raise. Syntax errors, type
errors and code-generation errors are expected results; an uncaught exception
is a bug.

Run it for a minute with:

    uv run --with atheris python tests/fuzz/fuzz_compiler.py \
        -max_total_time=60 tests/fuzz/corpus

CI runs the same command for two minutes on every push and ten on Mondays.
"""

import sys
from pathlib import Path

import atheris

# `tests/` is not a package: make the shared differential helpers importable
# when this file runs as a script instead of through pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with atheris.instrument_imports():
    from differential.emulator import Emulator, EmulatorError
    from pyngo.codegen import generate_object_code
    from pyngo.ir import IRError, generate_ir
    from pyngo.lexer import tokenize
    from pyngo.parser import Parser
    from pyngo.semantic import SemanticAnalyzer

# The HTTP layer rejects bodies over 64 KB; do not spend fuzzing time beyond it.
MAX_SOURCE = 64 * 1024


def compile_and_run(source: str) -> None:
    token_list, lexer_errors = tokenize(source)
    if lexer_errors:
        return

    is_valid, _ = Parser(token_list).analyze()
    if not is_valid:
        return

    analyzer = SemanticAnalyzer(token_list)
    is_valid, _ = analyzer.analyze()
    if not is_valid:
        return

    try:
        _ = generate_ir(analyzer.symbol_table, token_list)
    except IRError:
        pass  # a rejected IR is a result, not a crash

    is_valid, data, code, _ = generate_object_code(token_list, analyzer.symbol_table)
    if not is_valid:
        return

    try:
        _ = Emulator(data, code).run()
    except EmulatorError:
        # A real CPU would trap too: division by zero, an endless loop, a bad
        # opcode. The emulator raises instead of hanging, and that is fine.
        pass


def one_input(data: bytes) -> None:
    if len(data) > MAX_SOURCE:
        return

    compile_and_run(data.decode("utf-8", "replace"))


def main() -> None:
    atheris.Setup(sys.argv, one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
