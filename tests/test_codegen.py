"""Object code generator tests: addresses, bytes and jumps.

Run with:  pytest tests/ -q
"""

from pyngo.codegen import (
    CodeGenerator,
    PanelRow,
    Row,
    format_address,
    format_binary,
    format_hex,
    generate_object_code,
)
from pyngo.lexer import tokenize
from pyngo.parser import Parser
from pyngo.semantic import SemanticAnalyzer
from pyngo.tokens import Token

SYMBOL_TABLE = {"x": "int", "y": "int"}


def tokens_of(source: str) -> list[Token]:
    token_list, errors = tokenize(source)

    assert errors == []

    return token_list


def generate(
    source: str,
    symbol_table: dict[str, str],
) -> tuple[bool, list[PanelRow], list[PanelRow], list[str]]:
    return generate_object_code(tokens_of(source), symbol_table)


def assembled_rows(source: str, symbol_table: dict[str, str]) -> list[Row]:
    generator = CodeGenerator(tokens_of(source), symbol_table)
    rows = generator.generate()
    return [{"address": row[0], "bytes": row[1], "text": row[2]} for row in rows]


def real_symbol_table(source: str) -> tuple[list[Token], dict[str, str]]:
    """Run lexer → parser → semantic and return tokens and symbol table."""
    token_list = tokens_of(source)

    syntax_checker = Parser(token_list)
    is_valid, syntax_errors = syntax_checker.analyze()

    assert is_valid, syntax_errors

    type_checker = SemanticAnalyzer(token_list)
    is_valid, type_errors = type_checker.analyze()

    assert is_valid, type_errors

    return token_list, type_checker.symbol_table


# ==================================
# THE TWO EXAMPLES FROM THE ASSIGNMENT
# ==================================


def test_mul_example():
    ok, _, code, errors = generate("{ x = y & 3; }", SYMBOL_TABLE)

    assert ok, errors

    assert [row["hex"] for row in code[:4]] == [
        "A1 02 00",
        "BB 03 00",
        "F7 E3",
        "A3 00 00",
    ]
    assert [row["address"] for row in code[:4]] == [
        "0000 0000 0000 0000",
        "0000 0000 0000 0011",
        "0000 0000 0000 0110",
        "0000 0000 0000 1000",
    ]
    assert [row["content"] for row in code[:4]] == [
        "1010 0001  0000 0010  0000 0000",
        "1011 1011  0000 0011  0000 0000",
        "1111 0111  1110 0011",
        "1010 0011  0000 0000  0000 0000",
    ]


def test_div_example():
    ok, _, code, errors = generate("{ x = y | 3; }", SYMBOL_TABLE)

    assert ok, errors

    assert [row["hex"] for row in code[:5]] == [
        "A1 02 00",
        "BB 03 00",
        "BA 00 00",
        "F7 F3",
        "A3 00 00",
    ]
    assert [row["address"] for row in code[:5]] == [
        "0000 0000 0000 0000",
        "0000 0000 0000 0011",
        "0000 0000 0000 0110",
        "0000 0000 0000 1001",
        "0000 0000 0000 1011",
    ]
    assert code[2]["content"] == "1011 1010  0000 0000  0000 0000"


def test_variable_data():
    ok, data, _, errors = generate("{ x = 1; }", SYMBOL_TABLE)

    assert ok, errors

    assert [row["address"] for row in data] == [
        "0000 0000 0000 0000",
        "0000 0000 0000 0010",
    ]
    assert [row["content"] for row in data] == [
        "0000 0000  0000 0000",
        "0000 0000  0000 0000",
    ]
    assert [row["hex"] for row in data] == ["00 00", "00 00"]


def test_ends_with_hlt():
    ok, _, code, errors = generate("{ x = 1; }", SYMBOL_TABLE)

    assert ok, errors
    assert code[-1]["hex"] == "F4"
    assert code[-1]["text"] == "HLT"

    # Without print nobody calls print_routine: it is not emitted.
    assert all(row["text"] != "RET" for row in code)


# ==================================
# STATEMENTS
# ==================================


def test_declaration_stores_at_its_address():
    source = "{ int x = 5; }"
    token_list, symbol_table = real_symbol_table(source)

    ok, _, code, errors = generate_object_code(token_list, symbol_table)

    assert ok, errors

    assert code[0]["hex"] == "B8 05 00"  # MOV AX,5
    assert code[1]["hex"] == "A3 00 00"  # MOV [0000h],AX


def test_if_generates_cmp_and_jump():
    source = "{ if (x == 0) { y = 1; } }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    hexes = [row["hex"] for row in code]
    texts = [row["text"] for row in code]

    assert "3D 00 00" in hexes  # CMP AX,0
    assert any(text.startswith("JE ") for text in texts)


def test_while_jumps_back_to_start():
    source = "{ while (x == 0) { y = y @ 1; } }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    texts = [row["text"] for row in code]

    assert any(text.startswith("JE ") for text in texts)
    assert any(text.startswith("JMP ") for text in texts)


# Full assignment program, byte by byte and with its addresses.
def test_full_program_with_while():
    source = "{ int x = 5; while x > 0 { x = x # 1; }; }"
    token_list, symbol_table = real_symbol_table(source)

    ok, _, code, errors = generate_object_code(token_list, symbol_table)

    assert ok, errors

    assert [row["hex"] for row in code] == [
        "B8 05 00",  # 0000  MOV AX, 5
        "A3 00 00",  # 0003  MOV [0000h], AX
        "A1 00 00",  # 0006  MOV AX, [0000h]
        "3D 00 00",  # 0009  CMP AX, 0
        "0F 87 06 00",  # 000C  JA CMP_TRUE
        "B8 00 00",  # 0010  MOV AX, 0
        "E9 03 00",  # 0013  JMP CMP_END
        "B8 01 00",  # 0016  MOV AX, 1
        "3D 00 00",  # 0019  CMP AX, 0
        "0F 84 0C 00",  # 001C  JE WHILE_END
        "A1 00 00",  # 0020  MOV AX, [0000h]
        "2D 01 00",  # 0023  SUB AX, 1
        "A3 00 00",  # 0026  MOV [0000h], AX
        "E9 DA FF",  # 0029  JMP WHILE_START
        "F4",  # 002C  HLT
    ]
    assert [row["address"] for row in assembled_rows(source, symbol_table)] == [
        0x0000,
        0x0003,
        0x0006,
        0x0009,
        0x000C,
        0x0010,
        0x0013,
        0x0016,
        0x0019,
        0x001C,
        0x0020,
        0x0023,
        0x0026,
        0x0029,
        0x002C,
    ]


def test_print_uses_stack_and_routine():
    source = "{ print ( x ); }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    hexes = [row["hex"] for row in code]

    assert "50" in hexes  # PUSH AX
    assert "83 C4 02" in hexes  # ADD SP,2
    assert any(row["text"].startswith("CALL ") for row in code)

    # The routine reads its argument through BP, which addresses SS.
    assert "89 E5" in hexes  # MOV BP,SP
    assert "8B 46 02" in hexes  # MOV AX,[BP+2]


def test_print_uses_int_21h():
    source = "{ print ( x ); }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    hexes = [row["hex"] for row in code]
    texts = [row["text"] for row in code]

    assert hexes.count("CD 21") == 2  # tens and ones
    assert "B2 0A" in hexes  # MOV DL,10
    assert "F6 F2" in hexes  # DIV DL
    assert "80 C2 30" in hexes  # ADD DL,30H
    assert "MOV TENS, AL" in texts
    assert "MOV ONES, AH" in texts
    assert texts[-1] == "RET"


def test_print_adds_tens_and_ones_to_data():
    source = "{ int x = 1; print ( x ); }"
    token_list, symbol_table = real_symbol_table(source)

    ok, data, _, errors = generate_object_code(token_list, symbol_table)

    assert ok, errors

    # x takes 0000h-0001h; TENS and ONES are 1 byte each: 0002h and 0003h.
    assert [row["address"] for row in data] == [
        "0000 0000 0000 0000",
        "0000 0000 0000 0010",
        "0000 0000 0000 0011",
    ]
    assert [row["hex"] for row in data] == ["00 00", "00", "00"]


def test_print_of_out_of_range_literal():
    tokens = tokens_of("{ print ( 200 ); }")
    is_valid, errors = SemanticAnalyzer(tokens).analyze()
    assert not is_valid
    assert any("print only accepts a variable" in error for error in errors)


def test_print_of_operation_with_two_digits():
    ok, _, _, errors = generate("{ x = 200 # 100; print ( x ); }", SYMBOL_TABLE)

    assert ok, errors


# ==================================
# EXPRESSIONS
# ==================================


def test_compound_expression_uses_stack():
    source = "{ x = 2 & (y @ 1); }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    hexes = [row["hex"] for row in code]

    assert "50" in hexes  # PUSH AX
    assert "89 C3" in hexes  # MOV BX,AX
    assert "58" in hexes  # POP AX
    assert "F7 E3" in hexes  # MUL BX


def test_sum_with_variable_and_number():
    source = "{ x = y @ 5; }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    assert [row["hex"] for row in code[:3]] == [
        "A1 02 00",
        "05 05 00",
        "A3 00 00",
    ]


def test_comparison_against_sum():
    source = "{ if (x == y @ 1) { y = 2; } }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    hexes = [row["hex"] for row in code]

    assert "50" in hexes  # PUSH AX
    assert "89 C3" in hexes  # MOV BX,AX
    assert "58" in hexes  # POP AX
    assert "39 D8" in hexes  # CMP AX,BX


# The language handles 0..65535 and MUL/DIV are unsigned, so jumps are too.
def test_greater_uses_unsigned_jump():
    source = "{ if (x > y) { y = 1; } }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    texts = [row["text"] for row in code]

    assert any(text.startswith("JA ") for text in texts)
    assert not any(text.startswith("JG ") for text in texts)


def test_less_uses_unsigned_jump():
    source = "{ if (x < y) { y = 1; } }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    texts = [row["text"] for row in code]

    assert any(text.startswith("JB ") for text in texts)
    assert not any(text.startswith("JL ") for text in texts)


# The condition parentheses belong to FACTOR, not IF: they are not swallowed.
def test_if_with_parentheses_and_operator():
    source = "{ if (x @ 1) & (y @ 2) { y = 3; } }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    hexes = [row["hex"] for row in code]

    assert "F7 E3" in hexes  # MUL BX: the full condition arrived
    assert hexes[-1] == "F4"  # HLT: every token was consumed


def test_while_with_parentheses():
    source = "{ while (x @ 1) { y = y @ 1; } }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    hexes = [row["hex"] for row in code]

    assert hexes[-1] == "F4"  # HLT: every token was consumed
    assert hexes[-2].startswith("E9")  # JMP back to the start


# ==================================
# NEAR JUMPS
# ==================================


def test_near_jump_when_it_fits():
    source = "{ while (x == 0) { y = 1; } }"
    rows = assembled_rows(source, SYMBOL_TABLE)

    all_bytes = b"".join(bytes(row["bytes"]) for row in rows)

    assert b"\x0f\x84" in all_bytes  # near JE
    assert 0xE9 in all_bytes  # near JMP


def test_near_jump_when_it_does_not_fit():
    body = " y = y @ 1;" * 40
    source = "{ while (x == 0) {" + body + " } }"

    ok, _, code, errors = generate(source, SYMBOL_TABLE)

    assert ok, errors

    hexes = [row["hex"] for row in code]

    assert any(row.startswith("0F 84") for row in hexes)  # near JE
    assert any(row.startswith("E9") for row in hexes)  # near JMP


# ==================================
# ERRORS
# ==================================


def test_undeclared_variable():
    ok, _, _, errors = generate("{ z = 1; }", SYMBOL_TABLE)

    assert not ok
    assert any("has not been declared" in error for error in errors)


# Without this guard, source_of and emit_mul_div would raise KeyError.
def test_undeclared_variable_in_expression():
    ok, _, _, errors = generate("{ x = z @ 1; }", SYMBOL_TABLE)

    assert not ok
    assert errors == [
        "Line 1: OBJECT CODE ERROR: Variable 'z' has not been declared.",
    ]


def test_undeclared_variable_in_mul_div():
    ok, _, _, errors = generate("{ x = x & z; }", SYMBOL_TABLE)

    assert not ok
    assert errors == [
        "Line 1: OBJECT CODE ERROR: Variable 'z' has not been declared.",
    ]


# The generator stops at the first error.
def test_undeclared_variables_keep_their_line():
    source = "{\n x = z @ 1;\n y = w @ 2;\n}"

    ok, _, _, errors = generate(source, SYMBOL_TABLE)

    assert not ok
    assert errors == [
        "Line 2: OBJECT CODE ERROR: Variable 'z' has not been declared.",
    ]


def test_number_outside_16_bits():
    tokens = tokens_of("{ x = 70000; }")
    is_valid, errors = SemanticAnalyzer(tokens).analyze()
    assert not is_valid
    assert any("does not fit in 16 bits" in error for error in errors)


# ==================================
# FORMAT
# ==================================


def test_format_address():
    assert format_address(0x2000) == "0010 0000 0000 0000"
    assert format_address(0x0000) == "0000 0000 0000 0000"
    assert format_address(0x2002) == "0010 0000 0000 0010"


def test_format_binary():
    assert format_binary([0x89, 0x06, 0x00, 0x20]) == ("1000 1001  0000 0110  0000 0000  0010 0000")


def test_format_hex():
    assert format_hex([0x89, 0x06, 0x00, 0x20]) == "89 06 00 20"
