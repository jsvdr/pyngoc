# Encoder: one 16-bit x86 instruction -> its bytes (little endian).
# Operand: ("reg","AX") · ("mem",0x0000) · ("mem","BX",2) · ("imm",5)
# Format:  [opcode] [ModR/M] [displacement] [immediate]
from typing import Literal, TypeAlias

# Every shape an operand can have in the tables below.
Operand: TypeAlias = (
    tuple[Literal["reg"], str]
    | tuple[Literal["mem"], int]
    | tuple[Literal["mem"], str, int]
    | tuple[Literal["imm"], int]
    | tuple[Literal["id"], str]
    | tuple[Literal["num"], int]
    | tuple[Literal["bool"], int]
)


class EncoderError(Exception):
    """An operation that this table cannot encode."""


REG = {
    "AX": 0,
    "CX": 1,
    "DX": 2,
    "BX": 3,
    "SP": 4,
    "BP": 5,
    "SI": 6,
    "DI": 7,
    "AL": 0,
    "CL": 1,
    "DL": 2,
    "BL": 3,
    "AH": 4,
    "CH": 5,
    "DH": 6,
    "BH": 7,
}
REG8 = ("AL", "CL", "DL", "BL", "AH", "CH", "DH", "BH")
MEMORY_BASE = {"BX": 7, "BP": 6, "SI": 4, "DI": 5}
ALU = {"ADD": 0x00, "SUB": 0x28, "CMP": 0x38}  # base opcode; /digit = base >> 3
GROUP_F7 = {"MUL": 4, "DIV": 6}
ONE_BYTE = {"HLT": 0xF4, "RET": 0xC3}
JUMPS = {"JE": 0x84, "JNE": 0x85, "JB": 0x82, "JAE": 0x83, "JBE": 0x86, "JA": 0x87}


def bytes_of(value: int, count: int) -> list[int]:
    limit = 1 << (8 * count)
    if not -(limit // 2) <= value < limit:  # signed or unsigned
        raise EncoderError(f"Value {value} does not fit in {count} byte(s).")
    return [((value + limit) >> (8 * i)) & 0xFF for i in range(count)]


def modrm(mod: int, reg: int, rm: int) -> list[int]:
    return [(mod << 6) | (reg << 3) | rm]


def memory_operand(reg: int, operand: Operand) -> list[int]:
    if len(operand) == 2:  # [address]: mod 00, r/m 110
        return modrm(0b00, reg, 0b110) + bytes_of(int(operand[1]), 2)
    rm, displacement = MEMORY_BASE[str(operand[1])], int(operand[2])
    if -128 <= displacement <= 127:
        return modrm(0b01, reg, rm) + bytes_of(displacement, 1)
    return modrm(0b10, reg, rm) + bytes_of(displacement, 2)


def modrm_operand(operand: Operand, reg: int) -> list[int]:
    if operand[0] == "reg":
        return modrm(0b11, reg, REG[str(operand[1])])
    return memory_operand(reg, operand)


def width(*operands: Operand) -> int:
    """w = 0 if any operand is 8-bit, w = 1 if it is 16-bit."""
    return 0 if any(o[0] == "reg" and str(o[1]) in REG8 for o in operands) else 1


def _mov(destination: Operand, source: Operand) -> list[int]:
    w = width(destination, source)
    if destination[0] == "reg":
        destination_register = str(destination[1])
        if source[0] == "imm":  # B0/B8 + register
            return [0xB0 + 8 * w + REG[destination_register]] + bytes_of(int(source[1]), 1 + w)
        if source[0] == "reg":  # 88/89: source in reg, destination in r/m
            return [0x88 + w] + modrm(0b11, REG[str(source[1])], REG[destination_register])
        if destination_register == "AX" and len(source) == 2:  # A1: AX <- [address]
            return [0xA1] + bytes_of(int(source[1]), 2)
        return [0x8A + w] + memory_operand(REG[destination_register], source)  # 8A/8B
    if source[0] == "imm":  # C6/C7 /0
        return [0xC6 + w] + memory_operand(0, destination) + bytes_of(int(source[1]), 1 + w)
    if str(source[1]) == "AX" and len(destination) == 2:  # A3: [address] <- AX
        return [0xA3] + bytes_of(int(destination[1]), 2)
    return [0x88 + w] + memory_operand(REG[str(source[1])], destination)  # 88/89


def _alu(mnemonic: str, destination: Operand, source: Operand, force: str | None) -> list[int]:
    base, w = ALU[mnemonic], width(destination, source)
    if source[0] == "imm":
        if destination[0] == "reg" and REG[str(destination[1])] == 0:  # AL / AX: short form
            return [base + 4 + w] + bytes_of(int(source[1]), 1 + w)
        if force == "imm8":  # 83: one-byte signed immediate
            return [0x83] + modrm_operand(destination, base >> 3) + bytes_of(int(source[1]), 1)
        return [0x80 + w] + modrm_operand(destination, base >> 3) + bytes_of(int(source[1]), 1 + w)
    if source[0] == "mem":  # reg, mem
        return [base + 2 + w] + memory_operand(REG[str(destination[1])], source)
    return [base + w] + modrm_operand(destination, REG[str(source[1])])  # r/m, reg


def encode(mnemonic: str, operands: tuple[Operand, ...], force: str | None = None) -> list[int]:
    if mnemonic == "MOV":
        return _mov(operands[0], operands[1])
    if mnemonic in ALU:
        return _alu(mnemonic, operands[0], operands[1], force)
    if mnemonic in GROUP_F7:
        return [0xF6 + width(*operands)] + modrm_operand(operands[0], GROUP_F7[mnemonic])
    if mnemonic in ("PUSH", "POP"):
        return [(0x50 if mnemonic == "PUSH" else 0x58) + REG[str(operands[0][1])]]
    if mnemonic == "INT":
        return [0xCD] + bytes_of(int(operands[0][1]), 1)
    if mnemonic in ONE_BYTE:
        return [ONE_BYTE[mnemonic]]
    raise EncoderError(f"Cannot encode instruction {mnemonic}.")


def encode_jump(mnemonic: str, destination: int, position: int) -> list[int]:
    """Always near: CALL = E8 · JMP = E9 · Jcc = 0F + opcode, and rel16."""
    opcode = {"CALL": [0xE8], "JMP": [0xE9]}.get(mnemonic) or [0x0F, JUMPS[mnemonic]]
    return opcode + bytes_of(destination - (position + len(opcode) + 2), 2)


def jump_size(mnemonic: str) -> int:
    return 3 if mnemonic in ("CALL", "JMP") else 4
