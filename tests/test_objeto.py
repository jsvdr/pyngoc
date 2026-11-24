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
    filas = generador.generar()
    return [{"direccion": f[0], "bytes": f[1], "texto": f[2]} for f in filas]


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
        "A1 02 00",
        "BB 03 00",
        "F7 E3",
        "A3 00 00",
    ]
    assert [fila["direccion"] for fila in codigo[:4]] == [
        "0000 0000 0000 0000",
        "0000 0000 0000 0011",
        "0000 0000 0000 0110",
        "0000 0000 0000 1000",
    ]
    assert [fila["contenido"] for fila in codigo[:4]] == [
        "1010 0001  0000 0010  0000 0000",
        "1011 1011  0000 0011  0000 0000",
        "1111 0111  1110 0011",
        "1010 0011  0000 0000  0000 0000",
    ]


def test_ejemplo_div():
    ok, _, codigo, errores = generar("{ x = y | 3; }", TABLA)

    assert ok, errores

    assert [fila["hex"] for fila in codigo[:5]] == [
        "A1 02 00",
        "BB 03 00",
        "BA 00 00",
        "F7 F3",
        "A3 00 00",
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
        "0000 0000 0000 0000",
        "0000 0000 0000 0010",
    ]
    assert [fila["contenido"] for fila in datos] == [
        "0000 0000  0000 0000",
        "0000 0000  0000 0000",
    ]
    assert [fila["hex"] for fila in datos] == ["00 00", "00 00"]


def test_termina_con_hlt():
    ok, _, codigo, errores = generar("{ x = 1; }", TABLA)

    assert ok, errores
    assert codigo[-1]["hex"] == "F4"
    assert codigo[-1]["texto"] == "HLT"

    # Sin print nadie llama a rutina_print: no se emite.
    assert all(fila["texto"] != "RET" for fila in codigo)


# ==================================
# SENTENCIAS
# ==================================


def test_declaracion_guarda_en_su_direccion():
    fuente = "{ int x = 5; }"
    lista_tokens, tabla = tabla_real(fuente)

    ok, _, codigo, errores = generar_codigo_objeto(lista_tokens, tabla)

    assert ok, errores

    assert codigo[0]["hex"] == "B8 05 00"  # MOV AX,5
    assert codigo[1]["hex"] == "A3 00 00"  # MOV [0000h],AX


def test_if_genera_cmp_y_salto():
    fuente = "{ if (x == 0) { y = 1; } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]
    textos = [fila["texto"] for fila in codigo]

    assert "3D 00 00" in hexes  # CMP AX,0
    assert any(texto.startswith("JE ") for texto in textos)


def test_while_vuelve_al_inicio():
    fuente = "{ while (x == 0) { y = y @ 1; } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    textos = [fila["texto"] for fila in codigo]

    assert any(texto.startswith("JE ") for texto in textos)
    assert any(texto.startswith("JMP ") for texto in textos)


# Programa completo de la tarea, byte por byte y con sus direcciones.
def test_programa_completo_con_while():
    fuente = "{ int x = 5; while x > 0 { x = x # 1; }; }"
    lista_tokens, tabla = tabla_real(fuente)

    ok, _, codigo, errores = generar_codigo_objeto(lista_tokens, tabla)

    assert ok, errores

    assert [fila["hex"] for fila in codigo] == [
        "B8 05 00",  # 0000  MOV AX, 5
        "A3 00 00",  # 0003  MOV [0000h], AX
        "A1 00 00",  # 0006  MOV AX, [0000h]
        "3D 00 00",  # 0009  CMP AX, 0
        "0F 87 06 00",  # 000C  JA CMP_VERDADERO
        "B8 00 00",  # 0010  MOV AX, 0
        "E9 03 00",  # 0013  JMP CMP_FIN
        "B8 01 00",  # 0016  MOV AX, 1
        "3D 00 00",  # 0019  CMP AX, 0
        "0F 84 0C 00",  # 001C  JE WHILE_FIN
        "A1 00 00",  # 0020  MOV AX, [0000h]
        "2D 01 00",  # 0023  SUB AX, 1
        "A3 00 00",  # 0026  MOV [0000h], AX
        "E9 DA FF",  # 0029  JMP WHILE_INICIO
        "F4",  # 002C  HLT
    ]
    assert [fila["direccion"] for fila in filas_ensambladas(fuente, tabla)] == [
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


def test_print_usa_pila_y_rutina():
    fuente = "{ print ( x ); }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]

    assert "50" in hexes  # PUSH AX
    assert "83 C4 02" in hexes  # ADD SP,2
    assert any(fila["texto"].startswith("CALL ") for fila in codigo)


def test_print_imprime_con_int_21h():
    fuente = "{ print ( x ); }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]
    textos = [fila["texto"] for fila in codigo]

    assert hexes.count("CD 21") == 2  # decenas y unidades
    assert "B2 0A" in hexes  # MOV DL,10
    assert "F6 F2" in hexes  # DIV DL
    assert "80 C2 30" in hexes  # ADD DL,30H
    assert "MOV COC, AL" in textos
    assert "MOV RESI, AH" in textos
    assert textos[-1] == "RET"


def test_print_agrega_coc_y_resi_a_los_datos():
    fuente = "{ int x = 1; print ( x ); }"
    lista_tokens, tabla = tabla_real(fuente)

    ok, datos, _, errores = generar_codigo_objeto(lista_tokens, tabla)

    assert ok, errores

    # x ocupa 0000h-0001h; COC y RESI son de 1 byte: 0002h y 0003h.
    assert [fila["direccion"] for fila in datos] == [
        "0000 0000 0000 0000",
        "0000 0000 0000 0010",
        "0000 0000 0000 0011",
    ]
    assert [fila["hex"] for fila in datos] == ["00 00", "00", "00"]


def test_print_de_un_literal_fuera_de_rango():
    tokens = tokens_de("{ print ( 200 ); }")
    es_valido, errores = AnalizadorSemantico(tokens).analizar()
    assert not es_valido
    assert any("print solo acepta una variable" in e for e in errores)


def test_print_de_una_operacion_que_da_dos_cifras():
    ok, _, _, errores = generar("{ x = 200 # 100; print ( x ); }", TABLA)

    assert ok, errores


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
        "A1 02 00",
        "05 05 00",
        "A3 00 00",
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
    assert hexes[-1] == "F4"  # HLT: se consumieron todos los tokens


def test_while_con_parentesis():
    fuente = "{ while (x @ 1) { y = y @ 1; } }"

    ok, _, codigo, errores = generar(fuente, TABLA)

    assert ok, errores

    hexes = [fila["hex"] for fila in codigo]

    assert hexes[-1] == "F4"  # HLT: se consumieron todos los tokens
    assert hexes[-2].startswith("E9")  # JMP de vuelta al inicio


# ==================================
# SALTOS CORTOS Y CERCANOS
# ==================================


def test_salto_corto_cuando_entra():
    fuente = "{ while (x == 0) { y = 1; } }"
    filas = filas_ensambladas(fuente, TABLA)

    bytes_totales = b"".join(bytes(fila["bytes"]) for fila in filas)

    assert b"\x0f\x84" in bytes_totales  # JE cercano
    assert 0xE9 in bytes_totales  # JMP cercano


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
    assert errores == [
        "Línea 1: ERROR DE CÓDIGO OBJETO: La variable 'z' no ha sido declarada.",
    ]


def test_variable_no_declarada_en_mul_div():
    ok, _, _, errores = generar("{ x = x & z; }", TABLA)

    assert not ok
    assert errores == [
        "Línea 1: ERROR DE CÓDIGO OBJETO: La variable 'z' no ha sido declarada.",
    ]


# El generador detiene su ejecución al primer error.
def test_variables_no_declaradas_conservan_su_linea():
    fuente = "{\n x = z @ 1;\n y = w @ 2;\n}"

    ok, _, _, errores = generar(fuente, TABLA)

    assert not ok
    assert errores == [
        "Línea 2: ERROR DE CÓDIGO OBJETO: La variable 'z' no ha sido declarada.",
    ]


def test_numero_fuera_de_16_bits():
    tokens = tokens_de("{ x = 70000; }")
    es_valido, errores = AnalizadorSemantico(tokens).analizar()
    assert not es_valido
    assert any("no entra en 16 bits" in error for error in errores)


# ==================================
# FORMATO
# ==================================


def test_formatear_direccion():
    assert formatear_direccion(0x2000) == "0010 0000 0000 0000"
    assert formatear_direccion(0x0000) == "0000 0000 0000 0000"
    assert formatear_direccion(0x2002) == "0010 0000 0000 0010"


def test_formatear_binario():
    assert formatear_binario([0x89, 0x06, 0x00, 0x20]) == ("1000 1001  0000 0110  0000 0000  0010 0000")


def test_formatear_hex():
    assert formatear_hex([0x89, 0x06, 0x00, 0x20]) == "89 06 00 20"
