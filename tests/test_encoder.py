"""Encoder tests: every table example, in hex and in nibbles.

Run with:  pytest tests/ -q
"""

import pytest

from pyngo.encoder import (
    EncoderError,
    Operand,
    encode,
    encode_jump,
    jump_size,
)


def reg(name: str) -> Operand:
    return ("reg", name)


def mem(address: int) -> Operand:
    return ("mem", address)


def based(base: str, displacement: int) -> Operand:
    return ("mem", base, displacement)


def imm(value: int) -> Operand:
    return ("imm", value)


def hex_of(encoded_bytes: list[int]) -> str:
    return " ".join(f"{byte:02X}" for byte in encoded_bytes)


def nibbles_of(encoded_bytes: list[int]) -> str:
    # Two nibbles per byte, separated by ONE space; bytes separated by TWO.
    parts: list[str] = []

    for byte in encoded_bytes:
        parts.append(f"{byte >> 4:04b}")
        parts.append(f"{byte & 0x0F:04b}")

    return "  ".join(" ".join(parts[position : position + 2]) for position in range(0, len(parts), 2))


def check(
    mnemonic: str,
    operands: tuple[Operand, ...],
    expected: str,
    force: str | None = None,
) -> None:
    result = encode(mnemonic, operands, force=force)

    assert hex_of(result) == expected


# ==================================
# MOV
# ==================================


def test_mov_mem_reg():
    check("MOV", (mem(0x2000), reg("BX")), "89 1E 00 20")


def test_mov_reg_mem():
    check("MOV", (reg("BX"), mem(0x2000)), "8B 1E 00 20")


def test_mov_reg_reg():
    check("MOV", (reg("AX"), reg("BX")), "89 D8")


def test_mov_reg_imm():
    check("MOV", (reg("AX"), imm(5)), "B8 05 00")


def test_mov_mem_imm():
    check("MOV", (mem(0x2000), imm(5)), "C7 06 00 20 05 00")


def test_mov_mem_d8_reg():
    check("MOV", (based("BP", -4), reg("AX")), "89 46 FC")


def test_mov_reg_mem_d8():
    check("MOV", (reg("AX"), based("BP", -4)), "8B 46 FC")


def test_mov_mem_d8_imm():
    check("MOV", (based("BP", -4), imm(5)), "C7 46 FC 05 00")


def test_mov_ax_mem():
    check("MOV", (reg("AX"), mem(0x2000)), "A1 00 20")


def test_mov_mem_ax():
    check("MOV", (mem(0x2000), reg("AX")), "A3 00 20")


def test_mov_dx_zero():
    check("MOV", (reg("DX"), imm(0)), "BA 00 00")
    assert nibbles_of(encode("MOV", (reg("DX"), imm(0)))) == ("1011 1010  0000 0000  0000 0000")


# ==================================
# 8-bit MOV (used by print)
# ==================================


def test_mov_reg8_imm8():
    check("MOV", (reg("DL"), imm(10)), "B2 0A")
    check("MOV", (reg("AH"), imm(2)), "B4 02")


def test_mov_mem_reg8():
    check("MOV", (mem(0x2000), reg("AL")), "88 06 00 20")
    check("MOV", (mem(0x2000), reg("AH")), "88 26 00 20")


def test_mov_reg8_mem():
    check("MOV", (reg("DL"), mem(0x2000)), "8A 16 00 20")


def test_mov_reg8_reg8():
    check("MOV", (reg("DL"), reg("AL")), "88 C2")


# ==================================
# ADD (@)
# ==================================


def test_add_mem_reg():
    check("ADD", (mem(0x2000), reg("AX")), "01 06 00 20")


def test_add_reg_mem():
    check("ADD", (reg("AX"), mem(0x2000)), "03 06 00 20")


def test_add_reg_reg():
    check("ADD", (reg("AX"), reg("BX")), "01 D8")


def test_add_ax_imm():
    check("ADD", (reg("AX"), imm(5)), "05 05 00")


def test_add_reg_imm():
    check("ADD", (reg("BX"), imm(5)), "81 C3 05 00")


def test_add_mem_imm():
    check("ADD", (mem(0x2000), imm(5)), "81 06 00 20 05 00")


def test_add_reg_imm8():
    check("ADD", (reg("BX"), imm(5)), "83 C3 05", force="imm8")


def test_add_mem_imm8():
    check("ADD", (mem(0x2000), imm(5)), "83 06 00 20 05", force="imm8")


def test_add_ax_mem_d8():
    check("ADD", (reg("AX"), based("BP", -4)), "03 46 FC")


# ==================================
# SUB (#)
# ==================================


def test_sub_reg_reg():
    check("SUB", (reg("AX"), reg("BX")), "29 D8")


def test_sub_ax_imm():
    check("SUB", (reg("AX"), imm(5)), "2D 05 00")


def test_sub_reg_imm():
    check("SUB", (reg("BX"), imm(5)), "81 EB 05 00")


def test_sub_mem_imm():
    check("SUB", (mem(0x2000), imm(5)), "81 2E 00 20 05 00")


# ==================================
# CMP (==, >, <)
# ==================================


def test_cmp_reg_reg():
    check("CMP", (reg("AX"), reg("BX")), "39 D8")


def test_cmp_ax_imm():
    check("CMP", (reg("AX"), imm(0)), "3D 00 00")


def test_cmp_ax_mem():
    check("CMP", (reg("AX"), mem(0x2000)), "3B 06 00 20")


# ==================================
# MUL (&) and DIV (|)
# ==================================


def test_mul_reg():
    result = encode("MUL", (reg("BX"),))

    assert hex_of(result) == "F7 E3"
    assert nibbles_of(result) == "1111 0111  1110 0011"


def test_mul_cx():
    check("MUL", (reg("CX"),), "F7 E1")


def test_mul_direct_mem():
    result = encode("MUL", (mem(0x2000),))

    assert hex_of(result) == "F7 26 00 20"
    assert nibbles_of(result) == ("1111 0111  0010 0110  0000 0000  0010 0000")


def test_mul_mem_d8():
    check("MUL", (based("BP", -4),), "F7 66 FC")


def test_mul_mem_d16():
    check("MUL", (based("BP", 0x1234),), "F7 A6 34 12")


def test_div_reg():
    result = encode("DIV", (reg("BX"),))

    assert hex_of(result) == "F7 F3"
    assert nibbles_of(result) == "1111 0111  1111 0011"


def test_div_direct_mem():
    result = encode("DIV", (mem(0x2000),))

    assert hex_of(result) == "F7 36 00 20"
    assert nibbles_of(result) == ("1111 0111  0011 0110  0000 0000  0010 0000")


def test_div_mem_d8():
    check("DIV", (based("BP", -4),), "F7 76 FC")


def test_div_mem_d16():
    check("DIV", (based("BP", 0x1234),), "F7 B6 34 12")


# 8-bit DIV: F6 /6. Divides AX by DL (quotient in AL, remainder in AH).
def test_div_reg8():
    check("DIV", (reg("DL"),), "F6 F2")


# 8-bit ADD with immediate: 80 /0. Turns a digit into ASCII (+30H).
def test_add_reg8_imm8():
    check("ADD", (reg("DL"), imm(0x30)), "80 C2 30")


def test_int_21h():
    check("INT", (imm(0x21),), "CD 21")


# ==================================
# JUMPS, CALLS AND STACK
# ==================================


def test_near_jmp():
    # Displacement = 0x0103 - (0 + 3) = 0x0100
    assert hex_of(encode_jump("JMP", 0x0103, 0)) == "E9 00 01"


def test_near_je():
    # Displacement = 0x0104 - (0 + 4) = 0x0100
    assert hex_of(encode_jump("JE", 0x0104, 0)) == "0F 84 00 01"


def test_near_jne():
    assert hex_of(encode_jump("JNE", 0x0104, 0)) == "0F 85 00 01"


def test_near_ja():
    assert hex_of(encode_jump("JA", 0x0104, 0)) == "0F 87 00 01"


def test_near_jb():
    assert hex_of(encode_jump("JB", 0x0104, 0)) == "0F 82 00 01"


def test_near_jae():
    assert hex_of(encode_jump("JAE", 0x0104, 0)) == "0F 83 00 01"


def test_near_jbe():
    assert hex_of(encode_jump("JBE", 0x0104, 0)) == "0F 86 00 01"


def test_near_call():
    # Displacement = 0x0013 - (0 + 3) = 0x0010
    assert hex_of(encode_jump("CALL", 0x0013, 0)) == "E8 10 00"


def test_ret():
    check("RET", (), "C3")


def test_push_reg():
    check("PUSH", (reg("AX"),), "50")
    check("PUSH", (reg("BX"),), "53")
    check("PUSH", (reg("DX"),), "52")


def test_pop_reg():
    check("POP", (reg("AX"),), "58")
    check("POP", (reg("BX"),), "5B")
    check("POP", (reg("DX"),), "5A")


def test_hlt():
    check("HLT", (), "F4")


# ==================================
# SIZES AND ERRORS
# ==================================


def test_jump_sizes():
    assert jump_size("JMP") == 3
    assert jump_size("CALL") == 3
    assert jump_size("JE") == 4
    assert jump_size("JA") == 4


def test_imm8_out_of_range():
    with pytest.raises(EncoderError):
        _ = encode("ADD", (reg("BX"), imm(300)), force="imm8")


def test_large_immediate():
    with pytest.raises(EncoderError):
        _ = encode("MOV", (reg("AX"), imm(70000)))
