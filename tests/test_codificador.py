"""Pruebas del codificador: cada ejemplo de las tablas, en hex y en nibbles.

Se corre con:  pytest tests/ -q
"""

import os
import sys

import pytest

# Igual que test_smoke.py: se importa el backend por ruta explícita.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "backend"),
)

from codificador import (
    ErrorCodificador,
    Operando,
    codificar,
    codificar_salto,
    tamano_salto,
)


def reg(nombre: str) -> Operando:
    return ("reg", nombre)


def mem(direccion: int) -> Operando:
    return ("mem", direccion)


def dep(base: str, desplazamiento: int) -> Operando:
    return ("mem", base, desplazamiento)


def imm(valor: int) -> Operando:
    return ("imm", valor)


def hex_de(bytes_codificados: list[int]) -> str:
    return " ".join(f"{byte:02X}" for byte in bytes_codificados)


def nibbles_de(bytes_codificados: list[int]) -> str:
    # Dos nibbles por byte, separados por UN espacio; los bytes, por DOS.
    partes: list[str] = []

    for byte in bytes_codificados:
        partes.append(f"{byte >> 4:04b}")
        partes.append(f"{byte & 0x0F:04b}")

    return "  ".join(
        " ".join(partes[posicion : posicion + 2])
        for posicion in range(0, len(partes), 2)
    )


def comprobar(
    mnemonico: str,
    operandos: tuple[Operando, ...],
    esperado: str,
    forzar: str | None = None,
) -> None:
    resultado = codificar(mnemonico, operandos, forzar=forzar)

    assert hex_de(resultado) == esperado


# ==================================
# MOV
# ==================================


def test_mov_mem_reg():
    comprobar("MOV", (mem(0x2000), reg("AX")), "89 06 00 20", forzar="89")


def test_mov_reg_mem():
    comprobar("MOV", (reg("BX"), mem(0x2000)), "8B 1E 00 20")


def test_mov_reg_reg():
    comprobar("MOV", (reg("AX"), reg("BX")), "89 D8")


def test_mov_reg_reg_alterno():
    comprobar("MOV", (reg("AX"), reg("BX")), "8B C3", forzar="8b")


def test_mov_reg_imm():
    comprobar("MOV", (reg("AX"), imm(5)), "B8 05 00")


def test_mov_reg_imm_larga():
    comprobar("MOV", (reg("BX"), imm(5)), "C7 C3 05 00", forzar="c7")


def test_mov_mem_imm():
    comprobar("MOV", (mem(0x2000), imm(5)), "C7 06 00 20 05 00")


def test_mov_mem_d8_reg():
    comprobar("MOV", (dep("BP", -4), reg("AX")), "89 46 FC")


def test_mov_reg_mem_d8():
    comprobar("MOV", (reg("AX"), dep("BP", -4)), "8B 46 FC")


def test_mov_mem_d8_imm():
    comprobar("MOV", (dep("BP", -4), imm(5)), "C7 46 FC 05 00")


def test_mov_ax_mem():
    comprobar("MOV", (reg("AX"), mem(0x2000)), "A1 00 20")


def test_mov_mem_ax():
    comprobar("MOV", (mem(0x2000), reg("AX")), "A3 00 20")


def test_mov_dx_cero():
    comprobar("MOV", (reg("DX"), imm(0)), "BA 00 00")
    assert nibbles_de(codificar("MOV", (reg("DX"), imm(0)))) == (
        "1011 1010  0000 0000  0000 0000"
    )


# ==================================
# ADD (@)
# ==================================


def test_add_mem_reg():
    comprobar("ADD", (mem(0x2000), reg("AX")), "01 06 00 20")


def test_add_reg_mem():
    comprobar("ADD", (reg("AX"), mem(0x2000)), "03 06 00 20")


def test_add_reg_reg():
    comprobar("ADD", (reg("AX"), reg("BX")), "01 D8")


def test_add_reg_reg_alterno():
    comprobar("ADD", (reg("AX"), reg("BX")), "03 C3", forzar="03")


def test_add_ax_imm():
    comprobar("ADD", (reg("AX"), imm(5)), "05 05 00")


def test_add_reg_imm():
    comprobar("ADD", (reg("BX"), imm(5)), "81 C3 05 00")


def test_add_mem_imm():
    comprobar("ADD", (mem(0x2000), imm(5)), "81 06 00 20 05 00")


def test_add_reg_imm8():
    comprobar("ADD", (reg("BX"), imm(5)), "83 C3 05", forzar="imm8")


def test_add_mem_imm8():
    comprobar("ADD", (mem(0x2000), imm(5)), "83 06 00 20 05", forzar="imm8")


def test_add_ax_mem_d8():
    comprobar("ADD", (reg("AX"), dep("BP", -4)), "03 46 FC")


# ==================================
# SUB (#)
# ==================================


def test_sub_reg_reg():
    comprobar("SUB", (reg("AX"), reg("BX")), "29 D8")


def test_sub_ax_imm():
    comprobar("SUB", (reg("AX"), imm(5)), "2D 05 00")


def test_sub_reg_imm():
    comprobar("SUB", (reg("BX"), imm(5)), "81 EB 05 00")


def test_sub_mem_imm():
    comprobar("SUB", (mem(0x2000), imm(5)), "81 2E 00 20 05 00")


# ==================================
# CMP (==, >, <)
# ==================================


def test_cmp_reg_reg():
    comprobar("CMP", (reg("AX"), reg("BX")), "39 D8")


def test_cmp_ax_imm():
    comprobar("CMP", (reg("AX"), imm(0)), "3D 00 00")


def test_cmp_ax_mem():
    comprobar("CMP", (reg("AX"), mem(0x2000)), "3B 06 00 20")


# ==================================
# MUL (&) y DIV (|)
# ==================================


def test_mul_reg():
    resultado = codificar("MUL", (reg("BX"),))

    assert hex_de(resultado) == "F7 E3"
    assert nibbles_de(resultado) == "1111 0111  1110 0011"


def test_mul_cx():
    comprobar("MUL", (reg("CX"),), "F7 E1")


def test_mul_mem_directa():
    resultado = codificar("MUL", (mem(0x2000),))

    assert hex_de(resultado) == "F7 26 00 20"
    assert nibbles_de(resultado) == ("1111 0111  0010 0110  0000 0000  0010 0000")


def test_mul_mem_d8():
    comprobar("MUL", (dep("BP", -4),), "F7 66 FC")


def test_mul_mem_d16():
    comprobar("MUL", (dep("BP", 0x1234),), "F7 A6 34 12")


def test_div_reg():
    resultado = codificar("DIV", (reg("BX"),))

    assert hex_de(resultado) == "F7 F3"
    assert nibbles_de(resultado) == "1111 0111  1111 0011"


def test_div_mem_directa():
    resultado = codificar("DIV", (mem(0x2000),))

    assert hex_de(resultado) == "F7 36 00 20"
    assert nibbles_de(resultado) == ("1111 0111  0011 0110  0000 0000  0010 0000")


def test_div_mem_d8():
    comprobar("DIV", (dep("BP", -4),), "F7 76 FC")


def test_div_mem_d16():
    comprobar("DIV", (dep("BP", 0x1234),), "F7 B6 34 12")


# ==================================
# SALTOS, LLAMADAS Y PILA
# ==================================


def test_jmp_corto():
    assert hex_de(codificar_salto("JMP", 5, corto=True)) == "EB 05"


def test_jmp_cercano():
    assert hex_de(codificar_salto("JMP", 0x0100, corto=False)) == "E9 00 01"


def test_jmp_indirecto():
    comprobar("JMP", (reg("BX"),), "FF E3")


def test_je_corto():
    assert hex_de(codificar_salto("JE", 5, corto=True)) == "74 05"


def test_jne_corto():
    assert hex_de(codificar_salto("JNE", 5, corto=True)) == "75 05"


def test_jg_corto():
    assert hex_de(codificar_salto("JG", 5, corto=True)) == "7F 05"


def test_jl_corto():
    assert hex_de(codificar_salto("JL", 5, corto=True)) == "7C 05"


def test_jge_corto():
    assert hex_de(codificar_salto("JGE", 5, corto=True)) == "7D 05"


def test_jle_corto():
    assert hex_de(codificar_salto("JLE", 5, corto=True)) == "7E 05"


def test_ja_corto():
    assert hex_de(codificar_salto("JA", 5, corto=True)) == "77 05"


def test_jb_corto():
    assert hex_de(codificar_salto("JB", 5, corto=True)) == "72 05"


def test_jae_corto():
    assert hex_de(codificar_salto("JAE", 5, corto=True)) == "73 05"


def test_jbe_corto():
    assert hex_de(codificar_salto("JBE", 5, corto=True)) == "76 05"


def test_je_cercano():
    assert hex_de(codificar_salto("JE", 0x0100, corto=False)) == "0F 84 00 01"


def test_jne_cercano():
    assert hex_de(codificar_salto("JNE", 0x0100, corto=False)) == "0F 85 00 01"


def test_jg_cercano():
    assert hex_de(codificar_salto("JG", 0x0100, corto=False)) == "0F 8F 00 01"


def test_jl_cercano():
    assert hex_de(codificar_salto("JL", 0x0100, corto=False)) == "0F 8C 00 01"


def test_ja_cercano():
    assert hex_de(codificar_salto("JA", 0x0100, corto=False)) == "0F 87 00 01"


def test_jb_cercano():
    assert hex_de(codificar_salto("JB", 0x0100, corto=False)) == "0F 82 00 01"


def test_jae_cercano():
    assert hex_de(codificar_salto("JAE", 0x0100, corto=False)) == "0F 83 00 01"


def test_jbe_cercano():
    assert hex_de(codificar_salto("JBE", 0x0100, corto=False)) == "0F 86 00 01"


def test_call_cercano():
    assert hex_de(codificar_salto("CALL", 0x0010, corto=False)) == "E8 10 00"


def test_call_indirecto():
    comprobar("CALL", (reg("BX"),), "FF D3")


def test_ret():
    comprobar("RET", (), "C3")


def test_push_reg():
    comprobar("PUSH", (reg("AX"),), "50")


def test_push_mem():
    comprobar("PUSH", (mem(0x2000),), "FF 36 00 20")


def test_push_imm():
    comprobar("PUSH", (imm(5),), "68 05 00")


def test_push_imm8():
    comprobar("PUSH", (imm(5),), "6A 05", forzar="imm8")


def test_pop_reg():
    comprobar("POP", (reg("AX"),), "58")


def test_pop_mem():
    comprobar("POP", (mem(0x2000),), "8F 06 00 20")


def test_hlt():
    comprobar("HLT", (), "F4")


# ==================================
# TAMAÑOS Y ERRORES
# ==================================


def test_tamanos_de_salto():
    assert tamano_salto("JMP", corto=True) == 2
    assert tamano_salto("JMP", corto=False) == 3
    assert tamano_salto("JE", corto=True) == 2
    assert tamano_salto("JE", corto=False) == 4
    assert tamano_salto("CALL", corto=False) == 3


def test_imm8_fuera_de_rango():
    with pytest.raises(ErrorCodificador):
        codificar("ADD", (reg("BX"), imm(300)), forzar="imm8")


def test_inmediato_grande():
    with pytest.raises(ErrorCodificador):
        codificar("MOV", (reg("AX"), imm(70000)))
