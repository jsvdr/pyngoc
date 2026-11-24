# Codificador: una instrucción x86 de 16 bits -> sus bytes (little endian).
# Operando: ("reg","AX") · ("mem",0x0000) · ("mem","BX",2) · ("imm",5)
# Formato:  [opcode] [ModR/M] [desplazamiento] [inmediato]
from typing import TypeAlias

Operando: TypeAlias = tuple


class ErrorCodificador(Exception):
    """Operación que esta tabla no sabe codificar."""


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
BASE_MEMORIA = {"BX": 7, "BP": 6, "SI": 4, "DI": 5}
ALU = {"ADD": 0x00, "SUB": 0x28, "CMP": 0x38}  # opcode base; /dígito = base >> 3
GRUPO_F7 = {"MUL": 4, "DIV": 6}
UN_BYTE = {"HLT": 0xF4, "RET": 0xC3}
SALTOS = {"JE": 0x84, "JNE": 0x85, "JB": 0x82, "JAE": 0x83, "JBE": 0x86, "JA": 0x87}


def bytes_de(valor: int, cantidad: int) -> list[int]:
    limite = 1 << (8 * cantidad)
    if not -(limite // 2) <= valor < limite:  # con o sin signo
        raise ErrorCodificador(f"El valor {valor} no entra en {cantidad} byte(s).")
    return [((valor + limite) >> (8 * i)) & 0xFF for i in range(cantidad)]


def modrm(mod: int, reg: int, rm: int) -> list[int]:
    return [(mod << 6) | (reg << 3) | rm]


def operando_memoria(reg: int, operando: tuple) -> list[int]:
    if len(operando) == 2:  # [dirección]: mod 00, r/m 110
        return modrm(0b00, reg, 0b110) + bytes_de(operando[1], 2)
    rm, desplazamiento = BASE_MEMORIA[operando[1]], operando[2]
    if -128 <= desplazamiento <= 127:
        return modrm(0b01, reg, rm) + bytes_de(desplazamiento, 1)
    return modrm(0b10, reg, rm) + bytes_de(desplazamiento, 2)


def operando_modrm(operando: tuple, reg: int) -> list[int]:
    if operando[0] == "reg":
        return modrm(0b11, reg, REG[operando[1]])
    return operando_memoria(reg, operando)


def ancho(*operandos: tuple) -> int:
    """w = 0 si algún operando es de 8 bits, w = 1 si es de 16."""
    return 0 if any(o[0] == "reg" and o[1] in REG8 for o in operandos) else 1


def _mov(destino: tuple, fuente: tuple) -> list[int]:
    w = ancho(destino, fuente)
    if destino[0] == "reg":
        if fuente[0] == "imm":  # B0/B8 + registro
            return [0xB0 + 8 * w + REG[destino[1]]] + bytes_de(fuente[1], 1 + w)
        if fuente[0] == "reg":  # 88/89: origen en reg, destino en r/m
            return [0x88 + w] + modrm(0b11, REG[fuente[1]], REG[destino[1]])
        if destino[1] == "AX" and len(fuente) == 2:  # A1: AX <- [dirección]
            return [0xA1] + bytes_de(fuente[1], 2)
        return [0x8A + w] + operando_memoria(REG[destino[1]], fuente)  # 8A/8B
    if fuente[0] == "imm":  # C6/C7 /0
        return [0xC6 + w] + operando_memoria(0, destino) + bytes_de(fuente[1], 1 + w)
    if fuente[1] == "AX" and len(destino) == 2:  # A3: [dirección] <- AX
        return [0xA3] + bytes_de(destino[1], 2)
    return [0x88 + w] + operando_memoria(REG[fuente[1]], destino)  # 88/89


def _alu(mnemonico: str, destino: tuple, fuente: tuple, forzar: str | None) -> list[int]:
    base, w = ALU[mnemonico], ancho(destino, fuente)
    if fuente[0] == "imm":
        if destino[0] == "reg" and REG[destino[1]] == 0:  # AL / AX: forma corta
            return [base + 4 + w] + bytes_de(fuente[1], 1 + w)
        if forzar == "imm8":  # 83: inmediato de 1 byte con signo
            return [0x83] + operando_modrm(destino, base >> 3) + bytes_de(fuente[1], 1)
        return [0x80 + w] + operando_modrm(destino, base >> 3) + bytes_de(fuente[1], 1 + w)
    if fuente[0] == "mem":  # reg, mem
        return [base + 2 + w] + operando_memoria(REG[destino[1]], fuente)
    return [base + w] + operando_modrm(destino, REG[fuente[1]])  # r/m, reg


def codificar(mnemonico: str, operandos: tuple, forzar: str | None = None) -> list[int]:
    if mnemonico == "MOV":
        return _mov(*operandos)
    if mnemonico in ALU:
        return _alu(mnemonico, *operandos, forzar)
    if mnemonico in GRUPO_F7:
        return [0xF6 + ancho(*operandos)] + operando_modrm(operandos[0], GRUPO_F7[mnemonico])
    if mnemonico in ("PUSH", "POP"):
        return [(0x50 if mnemonico == "PUSH" else 0x58) + REG[operandos[0][1]]]
    if mnemonico == "INT":
        return [0xCD] + bytes_de(operandos[0][1], 1)
    if mnemonico in UN_BYTE:
        return [UN_BYTE[mnemonico]]
    raise ErrorCodificador(f"No sé codificar la instrucción {mnemonico}.")


def codificar_salto(mnemonico: str, destino: int, posicion: int) -> list[int]:
    """Siempre cercano: CALL = E8 · JMP = E9 · Jcc = 0F + opcode, y rel16."""
    opcode = {"CALL": [0xE8], "JMP": [0xE9]}.get(mnemonico) or [0x0F, SALTOS[mnemonico]]
    return opcode + bytes_de(destino - (posicion + len(opcode) + 2), 2)


def tamano_salto(mnemonico: str, corto: bool = False) -> int:
    return 3 if mnemonico in ("CALL", "JMP") else 4
