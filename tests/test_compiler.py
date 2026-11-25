"""Compiler smoke tests: cases that must always pass.

Run with:  pytest tests/ -q
"""

import pytest

from pyngo.ir import IRError, generate_ir
from pyngo.lexer import tokenize
from pyngo.parser import Parser
from pyngo.semantic import SemanticAnalyzer


def compile_to_semantic(
    source_text: str,
) -> tuple[bool, list[str], dict[str, str]]:
    """Run lexer → parser → semantic and return (is_valid, errors, symbol_table)."""
    token_list, lexer_errors = tokenize(source_text)

    assert lexer_errors == []

    syntax_checker = Parser(token_list)
    is_valid, syntax_errors = syntax_checker.analyze()

    assert is_valid, syntax_errors

    type_checker = SemanticAnalyzer(token_list)
    is_valid, type_errors = type_checker.analyze()

    return is_valid, type_errors, type_checker.symbol_table


def test_valid_program() -> None:
    is_valid, error_list, symbol_table = compile_to_semantic("{ int a = 1; bool b = true; }")

    assert is_valid
    assert error_list == ["Semantic OK"]
    assert symbol_table == {"a": "int", "b": "bool"}


def test_type_error_in_declaration() -> None:
    is_valid, error_list, _ = compile_to_semantic("{ int x = true; }")

    assert not is_valid
    assert error_list == ["Line 1: TYPE ERROR: Variable 'x' is int, but got bool."]


def test_undeclared_variable() -> None:
    is_valid, error_list, _ = compile_to_semantic("{ x = 10; }")

    assert not is_valid
    assert error_list == ["Line 1: DECLARATION ERROR: Variable 'x' has not been declared."]


def test_already_declared_variable() -> None:
    is_valid, error_list, _ = compile_to_semantic("{ int x = 1; int x = 2; }")

    assert not is_valid
    assert error_list == ["Line 1: DECLARATION ERROR: Variable 'x' has already been declared."]


def test_ir_table_has_3_fields() -> None:
    source = "{ int counter = 1; bool active = true; }"

    token_list, _ = tokenize(source)

    _, _, symbol_table = compile_to_semantic(source)

    rows = generate_ir(symbol_table, token_list)

    assert rows == [
        ("", "TITLE", "Pyngo"),
        ("", ".MODEL", "Small"),
        ("", ".486", ""),
        ("", ".STACK", ""),
        ("", "", ""),
        ("", ".DATA", ""),
        ("counter", "DW", "?"),
        ("active", "DB", "?"),
        ("", "", ""),
        ("", ".CODE", ""),
        ("MAIN", "PROC", "FAR"),
        ("", ".STARTUP", ""),
        ("", "", ""),
        ("", "MOV", "AX, 1"),
        ("", "MOV", "counter, AX"),
        ("", "MOV", "AL, 1"),
        ("", "MOV", "AH, 0"),
        ("", "MOV", "active, AL"),
        ("", "", ""),
        ("", ".EXIT", ""),
        ("MAIN", "ENDP", ""),
        ("", "", ""),
        ("", "END", ""),
    ]


def _print_rows(value: int) -> list[tuple[str, str, str]]:
    source = "{ int x = " + str(value) + "; print ( x ); }"

    token_list, _ = tokenize(source)

    _, _, symbol_table = compile_to_semantic(source)

    return generate_ir(symbol_table, token_list)


def test_print_uses_tens_and_ones() -> None:
    rows = _print_rows(42)

    assert rows == [
        ("", "TITLE", "Pyngo"),
        ("", ".MODEL", "Small"),
        ("", ".486", ""),
        ("", ".STACK", ""),
        ("", "", ""),
        ("", ".DATA", ""),
        ("x", "DW", "?"),
        ("TENS", "DB", "?"),
        ("ONES", "DB", "?"),
        ("", "", ""),
        ("", ".CODE", ""),
        ("MAIN", "PROC", "FAR"),
        ("", ".STARTUP", ""),
        ("", "", ""),
        ("", "MOV", "AX, 42"),
        ("", "MOV", "x, AX"),
        ("", "MOV", "AX, x"),
        ("", "MOV", "DL, 10"),
        ("", "DIV", "DL"),
        ("", "MOV", "TENS, AL"),
        ("", "MOV", "ONES, AH"),
        ("", "MOV", "DL, TENS"),
        ("", "ADD", "DL, 30H"),
        ("", "MOV", "AH, 02H"),
        ("", "INT", "21H"),
        ("", "MOV", "DL, ONES"),
        ("", "ADD", "DL, 30H"),
        ("", "MOV", "AH, 02H"),
        ("", "INT", "21H"),
        ("", "", ""),
        ("", ".EXIT", ""),
        ("MAIN", "ENDP", ""),
        ("", "", ""),
        ("", "END", ""),
    ]


def test_without_print_no_tens_or_ones() -> None:
    source = "{ int x = 1; }"

    token_list, _ = tokenize(source)

    _, _, symbol_table = compile_to_semantic(source)

    rows = generate_ir(symbol_table, token_list)

    assert all(name not in ("TENS", "ONES") for name, _, _ in rows)


def _rows(source: str) -> list[tuple[str, str, str]]:
    token_list, _ = tokenize(source)

    _, _, symbol_table = compile_to_semantic(source)

    return generate_ir(symbol_table, token_list)


def test_ir_rejects_print_literal_out_of_range() -> None:
    # print only accepts a variable (the result of operations)
    token_list, _ = tokenize("{ print ( 200 ); }")
    is_valid, error_list = Parser(token_list).analyze()
    assert not is_valid
    assert any("print only accepts a variable" in error for error in error_list)


def test_ir_accepts_two_digit_print() -> None:
    rows = _rows("{ int r = 99; print ( r ); }")

    assert ("", "MOV", "AX, r") in rows


def test_ir_does_not_confuse_a_large_first_operand() -> None:
    # 200 # 100 gives 100 and is assigned to a variable for printing
    rows = _rows("{ int r = 200 # 100; print ( r ); }")

    assert ("", "MOV", "AX, 200") in rows
    assert ("", "MOV", "AX, r") in rows


def test_ir_four_operators() -> None:
    rows = _rows("{ int a = 1; int b = 2; int c = a @ b; int d = a # b; int e = a & b; int f = a | b; }")

    # @ -> ADD, # -> SUB.
    assert ("", "ADD", "AX, b") in rows
    assert ("", "SUB", "AX, b") in rows

    # & -> MUL, | -> DIV (the operand goes through BX and DX is cleared first).
    assert ("", "MOV", "BX, b") in rows
    assert ("", "MUL", "BX") in rows
    assert ("", "MOV", "DX, 0") in rows
    assert ("", "DIV", "BX") in rows


def test_ir_if_with_labels() -> None:
    rows = _rows("{ int a = 1; int b = 2; int m = 0; if (a < b) { m = b; }; }")

    # Condition: MOV AX, a / CMP AX, b / unsigned jump if false (a < b -> JAE).
    assert ("", "CMP", "AX, b") in rows
    assert ("", "JAE", "IF_FALSE_1") in rows

    # True branch and false label at the end (no else).
    assert ("", "MOV", "m, AX") in rows
    assert ("IF_FALSE_1:", "", "") in rows

    cmp_index = rows.index(("", "CMP", "AX, b"))
    jump_index = rows.index(("", "JAE", "IF_FALSE_1"))
    true_index = rows.index(("", "MOV", "AX, b"))
    false_index = rows.index(("IF_FALSE_1:", "", ""))
    assert cmp_index < jump_index < true_index < false_index


def test_ir_while_with_labels() -> None:
    rows = _rows("{ int i = 0; while (i < 3) { i = i @ 1; }; }")

    # The while tests the condition at the start and repeats while it is true.
    assert ("WHILE_START_1:", "", "") in rows
    assert ("", "CMP", "AX, 3") in rows
    assert ("", "JAE", "WHILE_END_2") in rows

    # Body and jump back to the start.
    assert ("", "ADD", "AX, 1") in rows
    assert ("", "JMP", "WHILE_START_1") in rows
    assert ("WHILE_END_2:", "", "") in rows

    start_index = rows.index(("WHILE_START_1:", "", ""))
    cmp_index = rows.index(("", "CMP", "AX, 3"))
    jump_index = rows.index(("", "JAE", "WHILE_END_2"))
    back_index = rows.index(("", "JMP", "WHILE_START_1"))
    end_index = rows.index(("WHILE_END_2:", "", ""))
    assert start_index < cmp_index < jump_index < back_index < end_index


def test_type_error_in_while() -> None:
    is_valid, error_list, _ = compile_to_semantic("{ int a = 1; while (a) { a = 1; }; }")

    assert not is_valid
    assert error_list == ["Line 1: TYPE ERROR: The while condition must be bool."]


def test_ir_sum_and_subtraction_chain() -> None:
    rows = _rows("{ int a = 1; int b = 2; int c = 3; int d = a @ b # c; }")

    # @ and # have the same level: they chain from left to right.
    load_index = rows.index(("", "MOV", "AX, a"))
    add_index = rows.index(("", "ADD", "AX, b"))
    sub_index = rows.index(("", "SUB", "AX, c"))
    assert load_index < add_index < sub_index
    assert ("", "MOV", "d, AX") in rows


def test_ir_product_chain() -> None:
    rows = _rows("{ int a = 1; int b = 2; int c = 3; int d = a & b & c; }")

    assert rows.count(("", "MUL", "BX")) == 2
    assert ("", "MOV", "d, AX") in rows


def test_ir_rejects_nested_expression() -> None:
    source = "{ int a = 1; int b = 2; int c = 3; int d = a @ b & c; }"

    token_list, _ = tokenize(source)

    _, _, symbol_table = compile_to_semantic(source)

    with pytest.raises(IRError):
        _ = generate_ir(symbol_table, token_list)


def test_ir_rejects_parentheses() -> None:
    source = "{ int a = 1; int b = 2; int c = ( a @ b ); }"

    token_list, _ = tokenize(source)

    _, _, symbol_table = compile_to_semantic(source)

    with pytest.raises(IRError):
        _ = generate_ir(symbol_table, token_list)


def test_ir_rejects_compound_comparison() -> None:
    source = "{ int a = 1; int b = 2; int c = 3; if (a < b @ c) { a = 1; }; }"

    token_list, _ = tokenize(source)

    _, _, symbol_table = compile_to_semantic(source)

    with pytest.raises(IRError):
        _ = generate_ir(symbol_table, token_list)


# Parentheses must surround the whole condition: "(a @ 1) > 2" is not accepted.
def test_ir_rejects_partial_parentheses_in_condition() -> None:
    sources = (
        "{ int a = 1; if (a @ 1) > 2 { a = 0; }; }",
        "{ int a = 1; while (a @ 1) > 2 { a = 0; }; }",
    )

    for source in sources:
        token_list, _ = tokenize(source)

        _, _, symbol_table = compile_to_semantic(source)

        with pytest.raises(IRError):
            _ = generate_ir(symbol_table, token_list)


def test_lexer_rejects_non_ascii_identifiers() -> None:
    for source, expected in (
        ("{ int A = 1; }", "Line 1: Invalid character 'A'."),
        ("{ int ñ = 1; }", "Line 1: Invalid character 'ñ'."),
        ("{ int añ = 1; }", "Line 1: Invalid character 'ñ'."),
        ("{ int a² = 1; }", "Line 1: Invalid character '²'."),
    ):
        _, error_list = tokenize(source)

        assert error_list == [expected], source


def test_lexer_accepts_lowercase_and_digits() -> None:
    token_list, error_list = tokenize("{ int counter1 = 1; }")

    assert error_list == []
    assert any(token.lexeme == "counter1" for token in token_list)


def test_ir_bool_is_loaded_with_al() -> None:
    rows = _rows("{ bool p = true; bool r = p; }")

    # p is DB (1 byte): load AL and clear AH, so AX is 0 or 1.
    assert ("", "MOV", "AL, p") in rows
    assert ("", "MOV", "AH, 0") in rows
    assert ("", "MOV", "r, AL") in rows

    # A DB is never loaded with a 16-bit register.
    assert ("", "MOV", "AX, p") not in rows


def test_ir_bool_comparison_uses_al() -> None:
    rows = _rows("{ bool p = true; bool q = p == p; }")

    assert ("", "CMP", "AL, p") in rows
    assert ("", "SETE", "AL") in rows
    assert ("", "MOV", "q, AL") in rows

    assert ("", "CMP", "AX, p") not in rows


def test_ir_if_with_bool_uses_al() -> None:
    rows = _rows("{ int x = 1; bool p = false; if (p) { print ( x ); }; }")

    # The condition ends up complete in AX (0 or 1) and only then is compared with 0.
    jump_index = rows.index(("", "JE", "IF_FALSE_1"))

    assert rows[jump_index - 1] == ("", "CMP", "AX, 0")
    assert rows[jump_index - 2] == ("", "MOV", "AH, 0")
    assert rows[jump_index - 3] == ("", "MOV", "AL, p")


def test_ir_never_mixes_ax_with_a_bool() -> None:
    rows = _rows("{ bool p = true; bool q = p == p; if (p) { q = q == p; }; }")

    for _, operator, attribute in rows:
        if operator in ("MOV", "CMP") and attribute.startswith(("AX,", "BX,")):
            assert "p" not in attribute and "q" not in attribute
