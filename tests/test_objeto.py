"""Pruebas del generador de código objeto: direcciones, bytes y saltos.

Se corre con:  pytest tests/ -q
"""

import os
import sys

# Igual que test_smoke.py: se importa el backend por ruta explícita.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "backend"),
)

from objeto import (
    Fila,
    FilaPanel,
    GeneradorObjeto,
    ensamblar,
    formatear_binario,
    formatear_direccion,
    formatear_hex,
    generar_codigo_objeto,
)
from parser import Parser
from scanner import analizar_lexico
from semantico import AnalizadorSemantico
from tokens import Token

TABLA = {"x": "int", "y": "int"}


def tokens_de(fuente: str) -> list[Token]:
    lista_tokens, errores = analizar_lexico(fuente)

    assert errores == []

    return lista_tokens


def generar(
    fuente: str,
    tabla: dict[str, str],
) -> tuple[bool, list[FilaPanel], list[FilaPanel], list[str]]:
    return generar_codigo_objeto(tokens_de(fuente), tabla)


def filas_ensambladas(fuente: str, tabla: dict[str, str]) -> list[Fila]:
    generador = GeneradorObjeto(tokens_de(fuente), tabla)
    items, errores = generador.generar()

    assert errores == []

    return ensamblar(items)


def tabla_real(fuente: str) -> tuple[list[Token], dict[str, str]]:
    """Corre scanner → parser → semántico y devuelve tokens y tabla."""
    lista_tokens = tokens_de(fuente)

    revisor_sintaxis = Parser(lista_tokens)
    es_valido, errores_sintaxis = revisor_sintaxis.analizar()

    assert es_valido, errores_sintaxis

    revisor_tipos = AnalizadorSemantico(lista_tokens)
    es_valido, errores_tipos = revisor_tipos.analizar()

    assert es_valido, errores_tipos

    return lista_tokens, revisor_tipos.tabla


# ==================================
# LOS DOS EJEMPLOS DE LA TAREA
# ==================================


def test_ejemplo_mul():
    ok, _, codigo, errores = generar("{ x = y & 3; }", TABLA)

    assert ok, errores

    assert [fila["hex"] for fila in codigo[:4]] == [
        "A1 02 20",
        "BB 03 00",
        "F7 E3",
        "A3 00 20",
    ]
    assert [fila["direccion"] for fila in codigo[:4]] == [
        "0000 0000 0000 0000",
        "0000 0000 0000 0011",
        "0000 0000 0000 0110",
        "0000 0000 0000 1000",
    ]
    assert [fila["contenido"] for fila in codigo[:4]] == [
        "1010 0001  0000 0010  0010 0000",
        "1011 1011  0000 0011  0000 0000",
        "1111 0111  1110 0011",
        "1010 0011  0000 0000  0010 0000",
    ]


def test_ejemplo_div():
    ok, _, codigo, errores = generar("{ x = y | 3; }", TABLA)

    assert ok, errores

    assert [fila["hex"] for fila in codigo[:5]] == [
        "A1 02 20",
        "BB 03 00",
        "BA 00 00",
        "F7 F3",
        "A3 00 20",
    ]
    assert [fila["direccion"] for fila in codigo[:5]] == [
        "0000 0000 0000 0000",
        "0000 0000 0000 0011",
        "0000 0000 0000 0110",
        "0000 0000 0000 1001",
        "0000 0000 0000 1011",
    ]
    assert codigo[2]["contenido"] == "1011 1010  0000 0000  0000 0000"


def test_datos_de_las_variables():
    ok, datos, _, errores = generar("{ x = 1; }", TABLA)

    assert ok, errores

    assert [fila["direccion"] for fila in datos] == [
        "0010 0000 0000 0000",
        "0010 0000 0000 0010",
    ]
    assert [fila["contenido"] for fila in datos] == [
        "0000 0000  0000 0000",
        "0000 0000  0000 0000",
    ]
    assert [fila["hex"] for fila in datos] == ["00 00", "00 00"]


def test_termina_con_hlt_y_ret():
    ok, _, codigo, errores = generar("{ x = 1; }", TABLA)

    assert ok, errores
    assert [fila["hex"] for fila in codigo[-2:]] == ["F4", "C3"]
    assert [fila["texto"] for fila in codigo[-2:]] == ["HLT", "RET"]


# ==================================
# SENTENCIAS
# ==================================


def test_declaracion_guarda_en_su_direccion():
    fuente = "{ int x = 5; }"
    lista_tokens, tabla = tabla_real(fuente)

    ok, _, codigo, errores = generar_codigo_objeto(lista_tokens, tabla)

    assert ok, errores

    assert codigo[0]["hex"] == "B8 05 00"  # MOV AX,5
    assert codigo[1]["hex"] == "A3 00 20"  # MOV [2000h],AX


def test_if_genera_cmp_y_salto():
    fuente = "{ if (x == 0) { y = 1; } else { y = 2; } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]
    textos = [fila["texto"] for fila in codigo]

    assert "3D 00 00" in hexes  # CMP AX,0
    assert any(texto.startswith("JE ") for texto in textos)
    assert any(texto.startswith("JMP ") for texto in textos)


def test_while_vuelve_al_inicio():
    fuente = "{ while (x == 0) { y = y @ 1; } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    textos = [fila["texto"] for fila in codigo]

    assert any(texto.startswith("JE ") for texto in textos)
    assert any(texto.startswith("JMP ") for texto in textos)


def test_print_usa_pila_y_rutina():
    fuente = "{ print ( x ); }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]

    assert "50" in hexes  # PUSH AX
    assert "83 C4 02" in hexes  # ADD SP,2
    assert any(fila["texto"].startswith("CALL ") for fila in codigo)


# ==================================
# EXPRESIONES
# ==================================


def test_expresion_compuesta_usa_la_pila():
    fuente = "{ x = 2 & (y @ 1); }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]

    assert "50" in hexes  # PUSH AX
    assert "89 C3" in hexes  # MOV BX,AX
    assert "58" in hexes  # POP AX
    assert "F7 E3" in hexes  # MUL BX


def test_suma_con_variable_y_numero():
    fuente = "{ x = y @ 5; }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    assert [fila["hex"] for fila in codigo[:3]] == [
        "A1 02 20",
        "05 05 00",
        "A3 00 20",
    ]


def test_comparacion_contra_suma():
    fuente = "{ if (x == y @ 1) { y = 2; } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]

    assert "50" in hexes  # PUSH AX
    assert "89 C3" in hexes  # MOV BX,AX
    assert "58" in hexes  # POP AX
    assert "39 D8" in hexes  # CMP AX,BX


# El lenguaje maneja 0..65535 y MUL/DIV son sin signo: los saltos también.
def test_mayor_usa_salto_sin_signo():
    fuente = "{ if (x > y) { y = 1; } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    textos = [fila["texto"] for fila in codigo]

    assert any(texto.startswith("JA ") for texto in textos)
    assert not any(texto.startswith("JG ") for texto in textos)


def test_menor_usa_salto_sin_signo():
    fuente = "{ if (x < y) { y = 1; } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    textos = [fila["texto"] for fila in codigo]

    assert any(texto.startswith("JB ") for texto in textos)
    assert not any(texto.startswith("JL ") for texto in textos)


# Los paréntesis de la condición son de FACTOR, no de IF: no se comen.
def test_if_con_parentesis_y_operador():
    fuente = "{ if (x @ 1) & (y @ 2) { y = 3; } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]

    assert "F7 E3" in hexes  # MUL BX: la condición llegó completa
    assert hexes[-2] == "F4"  # HLT: se consumieron todos los tokens


def test_while_con_parentesis():
    fuente = "{ while (x @ 1) { y = y @ 1; } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]

    assert hexes[-2] == "F4"  # HLT: se consumieron todos los tokens
    assert hexes[-3].startswith("EB")  # JMP de vuelta al inicio


# ==================================
# SALTOS CORTOS Y CERCANOS
# ==================================


def test_salto_corto_cuando_entra():
    fuente = "{ while (x == 0) { y = 1; } }"
    filas = filas_ensambladas(fuente, TABLA)

    bytes_totales = b"".join(bytes(fila["bytes"]) for fila in filas)

    assert 0x74 in bytes_totales  # JE corto
    assert 0xEB in bytes_totales  # JMP corto


def test_salto_cercano_cuando_no_entra():
    cuerpo = " y = y @ 1;" * 40
    fuente = "{ while (x == 0) {" + cuerpo + " } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]

    assert any(fila.startswith("0F 84") for fila in hexes)  # JE cercano
    assert any(fila.startswith("E9") for fila in hexes)  # JMP cercano


# ==================================
# ERRORES
# ==================================


def test_variable_no_declarada():
    ok, _, _, errores = generar("{ z = 1; }", TABLA)

    assert not ok
    assert any("no ha sido declarada" in error for error in errores)


# Sin esta guarda, fuente_de y emitir_mul_div lanzarían KeyError.
def test_variable_no_declarada_en_la_expresion():
    ok, _, _, errores = generar("{ x = z @ 1; }", TABLA)

    assert not ok
    assert errores == ["La variable 'z' no ha sido declarada."]


def test_variable_no_declarada_en_mul_div():
    ok, _, _, errores = generar("{ x = x & z; }", TABLA)

    assert not ok
    assert errores == ["La variable 'z' no ha sido declarada."]


def test_numero_fuera_de_16_bits():
    ok, _, _, errores = generar("{ x = 70000; }", TABLA)

    assert not ok
    assert any("no entra en 16 bits" in error for error in errores)


# ==================================
# FORMATO
# ==================================


def test_formatear_direccion():
    assert formatear_direccion(0x2000) == "0010 0000 0000 0000"
    assert formatear_direccion(0x0000) == "0000 0000 0000 0000"
    assert formatear_direccion(0x2002) == "0010 0000 0000 0010"


def test_formatear_binario():
    assert formatear_binario([0x89, 0x06, 0x00, 0x20]) == (
        "1000 1001  0000 0110  0000 0000  0010 0000"
    )


def test_formatear_hex():
    assert formatear_hex([0x89, 0x06, 0x00, 0x20]) == "89 06 00 20"
