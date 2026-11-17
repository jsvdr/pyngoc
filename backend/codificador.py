# Codificador: una instrucción x86 de 16 bits -> sus bytes.
# No decide QUÉ instrucción va: eso lo hace objeto.py.
# Las variantes están en tablas de datos (ALUM, GRUPO_F7, SALTOS...),
# no en una cadena de ifs sueltos.
#
# Un operando es una tupla:
#   ("reg", "AX")       registro de 16 bits
#   ("mem", 0x2000)     [2000h]    (dirección directa)
#   ("mem", "BP", -4)   [BP-4]     (base + desplazamiento)
#   ("imm", 5)          número
#
# Formato: [opcode] [ModR/M] [desplazamiento] [inmediato]
# Todo en 16 bits (w = 1) y little endian.

from typing import Literal, TypeAlias

Operando: TypeAlias = (
    tuple[Literal["reg"], str]
    | tuple[Literal["mem"], int]
    | tuple[Literal["mem"], str, int]
    | tuple[Literal["imm"], int]
    | tuple[Literal["id"], str]
    | tuple[Literal["num"], int]
    | tuple[Literal["bool"], int]
)


class ErrorCodificador(Exception):
    """Operación que esta tabla no sabe codificar."""


# Número de registro dentro de ModR/M (mod = 11) y dentro de +r.
REG16 = {"AX": 0, "CX": 1, "DX": 2, "BX": 3, "SP": 4, "BP": 5, "SI": 6, "DI": 7}

# Registros de 8 bits. Los cuatro últimos (AH, CH, DH, BH) son la mitad alta.
# Los usa el print, que trabaja cifra por cifra.
REG8 = {"AL": 0, "CL": 1, "DL": 2, "BL": 3, "AH": 4, "CH": 5, "DH": 6, "BH": 7}


def es_registro8(operando: Operando) -> bool:
    return operando[0] == "reg" and operando[1] in REG8


def numero_registro(nombre: str) -> int:
    if nombre in REG8:
        return REG8[nombre]

    return REG16[nombre]


# Los números de la tabla de memoria 16 bits NO son los mismos:
# 110 es [BP] (si mod != 00) y 111 es [BX].
BASE_MEMORIA = {"BX": 7, "BP": 6, "SI": 4, "DI": 5}

# ADD, SUB y CMP comparten formato. Cada tupla es:
# (op r/m,r  | op r,r/m | op AX,imm)
ALUM = {
    "ADD": (0x01, 0x03, 0x05),
    "SUB": (0x29, 0x2B, 0x2D),
    "CMP": (0x39, 0x3B, 0x3D),
}

# /dígito dentro del grupo 81 (inmediato de 16 bits) y 83 (inmediato de 8).
DIGITO_ALU = {"ADD": 0x0, "SUB": 0x5, "CMP": 0x7}

# Grupo F7: un solo operando r/m16.
GRUPO_F7 = {"MUL": 0x4, "DIV": 0x6}

# Grupo FF: CALL/JMP/PUSH por registro o memoria.
GRUPO_FF = {"CALL": 0x2, "JMP": 0x4, "PUSH": 0x6}

# Saltos cortos: opcode de un byte + cb.
# Los saltos con signo (JL/JG) quedan en la tabla, pero el generador usa
# los sin signo (JB/JA): el lenguaje maneja valores 0..65535 y MUL/DIV
# son sin signo.
SALTOS_CORTOS = {
    "JE": 0x74,
    "JZ": 0x74,
    "JNE": 0x75,
    "JNZ": 0x75,
    "JL": 0x7C,
    "JGE": 0x7D,
    "JLE": 0x7E,
    "JG": 0x7F,
    "JB": 0x72,
    "JAE": 0x73,
    "JBE": 0x76,
    "JA": 0x77,
}

# Saltos cercanos: 0F + segundo byte + cw (80386 o superior).
SALTOS_CERCANOS = {
    "JE": 0x84,
    "JZ": 0x84,
    "JNE": 0x85,
    "JNZ": 0x85,
    "JL": 0x8C,
    "JGE": 0x8D,
    "JLE": 0x8E,
    "JG": 0x8F,
    "JB": 0x82,
    "JAE": 0x83,
    "JBE": 0x86,
    "JA": 0x87,
}

JMP_CORTO = 0xEB
JMP_CERCANO = 0xE9
CALL_CERCANO = 0xE8


# Número -> bytes en little endian. Acepta negativos (complemento a 2).
def bytes_de(valor: int, cantidad: int) -> list[int]:
    limite = 1 << (8 * cantidad)

    if valor < 0:
        valor += limite

    if not 0 <= valor < limite:
        raise ErrorCodificador(
            f"El valor {valor} no entra en {cantidad} byte(s).",
        )

    return [(valor >> (8 * posicion)) & 0xFF for posicion in range(cantidad)]


# Byte ModR/M: mod(2) | reg(3) | r/m(3).
def modrm(mod: int, reg: int, rm: int) -> list[int]:
    return [(mod << 6) | (reg << 3) | rm]


# ModR/M + desplazamiento de un operando de memoria.
def operando_memoria(reg: int, operando: Operando) -> list[int]:
    if operando[0] != "mem":
        raise ErrorCodificador(f"No es un operando de memoria: {operando}.")

    # ("mem", dirección): mod 00, r/m 110 + D16.
    if len(operando) == 2:
        return modrm(0b00, reg, 0b110) + bytes_de(operando[1], 2)

    # ("mem", base, desplazamiento): mod 01 (D8) o mod 10 (D16).
    rm = BASE_MEMORIA[operando[1]]
    desplazamiento = operando[2]

    # [BP] solo no se puede con mod 00: por eso el 0 usa mod 01.
    if -128 <= desplazamiento <= 127:
        return modrm(0b01, reg, rm) + bytes_de(desplazamiento, 1)

    return modrm(0b10, reg, rm) + bytes_de(desplazamiento, 2)


# ModR/M del destino cuando el otro campo es un registro fijo.
def operando_modrm(operando: Operando, reg: int) -> list[int]:
    if operando[0] == "reg":
        return modrm(0b11, reg, numero_registro(operando[1]))

    if operando[0] == "mem":
        return operando_memoria(reg, operando)

    raise ErrorCodificador(f"No se puede usar un inmediato como destino: {operando}.")


# MOV de 8 bits: registros AL/AH/... y bytes en memoria.
# El ancho se reconoce por el nombre del registro (AL es byte, AX es palabra).
def _codificar_mov8(destino: Operando, fuente: Operando) -> list[int]:
    if destino[0] == "reg" and not es_registro8(destino):
        raise ErrorCodificador("MOV no mezcla registros de 8 y 16 bits.")

    if fuente[0] == "reg" and not es_registro8(fuente):
        raise ErrorCodificador("MOV no mezcla registros de 8 y 16 bits.")

    # reg8, imm8: B0+r.
    if destino[0] == "reg" and fuente[0] == "imm":
        return [0xB0 + REG8[destino[1]]] + bytes_de(fuente[1], 1)

    # reg8, reg8.
    if destino[0] == "reg" and fuente[0] == "reg":
        return [0x8A] + modrm(0b11, REG8[destino[1]], REG8[fuente[1]])

    # reg8, mem.
    if destino[0] == "reg" and fuente[0] == "mem":
        return [0x8A] + operando_memoria(REG8[destino[1]], fuente)

    # mem, reg8.
    if destino[0] == "mem" and fuente[0] == "reg":
        return [0x88] + operando_memoria(REG8[fuente[1]], destino)

    raise ErrorCodificador(
        f"MOV de 8 bits no acepta {destino[0]} como destino y {fuente[0]} como fuente.",
    )


# MOV tiene muchas formas: se elige por los tipos de operando.
def _codificar_mov(
    destino: Operando,
    fuente: Operando,
    forzar: str | None,
) -> list[int]:
    if es_registro8(destino) or es_registro8(fuente):
        return _codificar_mov8(destino, fuente)

    # reg, reg: 89 es lo normal (d = 0); 8B es la forma alterna (d = 1).
    if destino[0] == "reg" and fuente[0] == "reg":
        if forzar == "8b":
            return [0x8B] + modrm(0b11, REG16[destino[1]], REG16[fuente[1]])

        return [0x89] + modrm(0b11, REG16[fuente[1]], REG16[destino[1]])

    # reg, mem: si es AX y la memoria es directa, A1 es más corto.
    if destino[0] == "reg" and fuente[0] == "mem":
        if forzar is None and destino[1] == "AX" and len(fuente) == 2:
            return [0xA1] + bytes_de(fuente[1], 2)

        return [0x8B] + operando_memoria(REG16[destino[1]], fuente)

    # mem, reg: si es AX y la memoria es directa, A3 es más corto.
    if destino[0] == "mem" and fuente[0] == "reg":
        if forzar is None and fuente[1] == "AX" and len(destino) == 2:
            return [0xA3] + bytes_de(destino[1], 2)

        return [0x89] + operando_memoria(REG16[fuente[1]], destino)

    # reg, imm: B8+r es lo normal; C7 /0 es la forma larga.
    if destino[0] == "reg" and fuente[0] == "imm":
        if forzar == "c7":
            return (
                [0xC7]
                + modrm(0b11, 0, REG16[destino[1]])
                + bytes_de(
                    fuente[1],
                    2,
                )
            )

        return [0xB8 + REG16[destino[1]]] + bytes_de(fuente[1], 2)

    # mem, imm: siempre C7 /0.
    if destino[0] == "mem" and fuente[0] == "imm":
        return [0xC7] + operando_memoria(0, destino) + bytes_de(fuente[1], 2)

    raise ErrorCodificador(
        f"MOV no acepta {destino[0]} como destino y {fuente[0]} como fuente.",
    )


# ADD, SUB y CMP.
def _codificar_alu(
    mnemonico: str,
    destino: Operando,
    fuente: Operando,
    forzar: str | None,
) -> list[int]:
    opcode_rm_reg, opcode_reg_rm, opcode_ax_imm = ALUM[mnemonico]
    digito = DIGITO_ALU[mnemonico]

    # Versión de 8 bits: solo hace falta "op r/m8, imm8" (80 /d), que es la que
    # usa el print para pasar la cifra a ASCII con "ADD DL, 30H".
    if es_registro8(destino) or es_registro8(fuente):
        if fuente[0] != "imm":
            raise ErrorCodificador(
                f"{mnemonico} de 8 bits solo se codifica con un inmediato.",
            )

        valor = fuente[1]

        if destino[0] == "reg" and destino[1] == "AL" and forzar is None:
            return [opcode_ax_imm - 1] + bytes_de(valor, 1)

        return [0x80] + operando_modrm(destino, digito) + bytes_de(valor, 1)

    # op AX, imm16: la forma corta cuando el destino es AX.
    if fuente[0] == "imm":
        valor = fuente[1]

        if destino[0] == "reg" and destino[1] == "AX" and forzar is None:
            return [opcode_ax_imm] + bytes_de(valor, 2)

        # 83: inmediato de 8 bits con signo (-128..127).
        if forzar == "imm8":
            if not -128 <= valor <= 127:
                raise ErrorCodificador(
                    f"El inmediato {valor} no entra con signo en 8 bits.",
                )

            return [0x83] + operando_modrm(destino, digito) + bytes_de(valor, 1)

        # 81: inmediato de 16 bits.
        return [0x81] + operando_modrm(destino, digito) + bytes_de(valor, 2)

    # op reg, mem (d = 1).
    if fuente[0] == "mem" and destino[0] == "reg":
        return [opcode_reg_rm] + operando_memoria(REG16[destino[1]], fuente)

    # op reg, reg (d = 1): la forma alterna de ADD AX,BX.
    if fuente[0] == "reg" and destino[0] == "reg" and forzar == "03":
        return [opcode_reg_rm] + modrm(
            0b11,
            REG16[destino[1]],
            REG16[fuente[1]],
        )

    # op r/m, reg (d = 0): mem, reg y reg, reg.
    if destino[0] in ("reg", "mem") and fuente[0] == "reg":
        return [opcode_rm_reg] + operando_modrm(destino, REG16[fuente[1]])

    raise ErrorCodificador(f"{mnemonico} no acepta esa combinación de operandos.")


# MUL y DIV: opcode F7 + /dígito + r/m16. Con un registro de 8 bits, F6.
def _codificar_grupo_f7(mnemonico: str, operando: Operando) -> list[int]:
    if es_registro8(operando):
        return [0xF6] + operando_modrm(operando, GRUPO_F7[mnemonico])

    return [0xF7] + operando_modrm(operando, GRUPO_F7[mnemonico])


# CALL, JMP y PUSH por registro o memoria: opcode FF + /dígito.
def _codificar_grupo_ff(mnemonico: str, operando: Operando) -> list[int]:
    return [0xFF] + operando_modrm(operando, GRUPO_FF[mnemonico])


def codificar(
    mnemonico: str,
    operandos: tuple[Operando, ...],
    forzar: str | None = None,
) -> list[int]:
    """Devuelve los bytes de una instrucción. forzar elige la variante larga."""
    if mnemonico == "MOV":
        return _codificar_mov(operandos[0], operandos[1], forzar)

    if mnemonico in ALUM:
        return _codificar_alu(mnemonico, operandos[0], operandos[1], forzar)

    if mnemonico in GRUPO_F7:
        return _codificar_grupo_f7(mnemonico, operandos[0])

    # PUSH y POP van antes que GRUPO_FF: comparten el FF pero tienen
    # además las formas cortas 50+r y 58+r.
    if mnemonico == "PUSH":
        operando = operandos[0]

        if operando[0] == "reg":
            return [0x50 + REG16[operando[1]]]

        if operando[0] == "mem":
            return [0xFF] + operando_memoria(GRUPO_FF["PUSH"], operando)

        if operando[0] == "imm":
            if forzar == "imm8":
                return [0x6A] + bytes_de(operando[1], 1)

            return [0x68] + bytes_de(operando[1], 2)

    if mnemonico == "POP":
        operando = operandos[0]

        if operando[0] == "reg":
            return [0x58 + REG16[operando[1]]]

        if operando[0] == "mem":
            return [0x8F] + operando_memoria(0, operando)

    if mnemonico in GRUPO_FF:
        return _codificar_grupo_ff(mnemonico, operandos[0])

    # Interrupción por número: INT 21H -> CD 21.
    if mnemonico == "INT":
        if operandos[0][0] != "imm":
            raise ErrorCodificador("INT necesita un número.")

        return [0xCD] + bytes_de(operandos[0][1], 1)

    if mnemonico == "HLT":
        return [0xF4]

    if mnemonico == "RET":
        return [0xC3]

    raise ErrorCodificador(f"No sé codificar la instrucción {mnemonico}.")


# Salto relativo: rel = destino - dirección de la siguiente instrucción.
def codificar_salto(mnemonico: str, relativo: int, corto: bool) -> list[int]:
    if mnemonico == "CALL":
        return [CALL_CERCANO] + bytes_de(relativo, 2)

    if mnemonico == "JMP":
        if corto:
            return [JMP_CORTO] + bytes_de(relativo, 1)

        return [JMP_CERCANO] + bytes_de(relativo, 2)

    if corto:
        return [SALTOS_CORTOS[mnemonico]] + bytes_de(relativo, 1)

    return [0x0F, SALTOS_CERCANOS[mnemonico]] + bytes_de(relativo, 2)


# Cuántos bytes ocupa un salto, para la primera pasada.
def tamano_salto(mnemonico: str, corto: bool) -> int:
    if mnemonico == "CALL":
        return 3

    if mnemonico == "JMP":
        return 2 if corto else 3

    return 2 if corto else 4
