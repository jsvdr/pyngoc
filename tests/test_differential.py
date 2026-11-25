"""Differential test: random programs through the compiler and an x86-16 emulator.

The generator (with a fixed seed, so the test is reproducible) builds programs
the language accepts. Each one is compiled to object code, emulated byte by
byte, and compared with the reference interpreter in `differential/reference.py`:

- the text printed by INT 21H / AH=02H,
- the final value of every variable in the data segment.

Both checks are needed: the values catch mistakes that never reach `print`.
"""

import pytest

from differential.emulator import Emulator
from differential.generator import generate_programs
from differential.reference import Interpreter, Program, render_source
from pyngo.codegen import PanelRow, generate_object_code
from pyngo.lexer import tokenize
from pyngo.parser import Parser
from pyngo.semantic import SemanticAnalyzer

SEED = 20260101
PROGRAM_COUNT = 300

PROGRAMS = generate_programs(PROGRAM_COUNT, SEED)


def compile_to_object_code(source: str) -> tuple[list[PanelRow], list[PanelRow], dict[str, str]]:
    token_list, lexer_errors = tokenize(source)
    assert lexer_errors == []

    is_valid, parser_errors = Parser(token_list).analyze()
    assert is_valid, parser_errors

    analyzer = SemanticAnalyzer(token_list)
    is_valid, semantic_errors = analyzer.analyze()
    assert is_valid, semantic_errors

    is_valid, data, code, codegen_errors = generate_object_code(token_list, analyzer.symbol_table)
    assert is_valid, codegen_errors

    return data, code, analyzer.symbol_table


def read_variables(emulator: Emulator, symbol_table: dict[str, str]) -> dict[str, int | bool]:
    """Walk the data segment in declaration order, like codegen.py lays it out."""
    values: dict[str, int | bool] = {}
    address = 0

    for name, data_type in symbol_table.items():
        is_int = data_type == "int"
        raw = emulator.read_variable(address, wide=is_int)
        values[name] = raw if is_int else bool(raw)
        address += 2 if is_int else 1

    return values


@pytest.mark.parametrize("program", PROGRAMS, ids=[f"program-{index}" for index in range(PROGRAM_COUNT)])
def test_emulator_matches_reference(program: Program) -> None:
    source = render_source(program)

    data, code, symbol_table = compile_to_object_code(source)
    emulator = Emulator(data, code)
    output = emulator.run()

    expected = Interpreter(program).run()

    assert output == expected.output, source
    assert read_variables(emulator, symbol_table) == expected.variables, source
