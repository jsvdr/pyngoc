"""Humo del compilador: 5 casos que siempre deben pasar.

Se corre con:  pytest tests/ -q
"""

import os
import sys

# Los tests importan el backend por ruta explícita a propósito:
# así no hay que convertir backend/ en paquete ni tocar app.py.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "backend"),
)

from intermedio import generar_codigo_intermedio
from parser import Parser
from scanner import analizar_lexico
from semantico import AnalizadorSemantico


def compilar_hasta_semantico(
    texto_fuente: str,
) -> tuple[bool, list[str], dict[str, str]]:
    """Corre scanner → parser → semántico y devuelve (es_valido, errores, tabla)."""
    lista_tokens, lista_errores_lexico = analizar_lexico(texto_fuente)

    assert lista_errores_lexico == []

    revisor_sintaxis = Parser(lista_tokens)
    es_valido, lista_errores_sintaxis = revisor_sintaxis.analizar()

    assert es_valido, lista_errores_sintaxis

    revisor_tipos = AnalizadorSemantico(lista_tokens)
    es_valido, lista_errores_tipos = revisor_tipos.analizar()

    return es_valido, lista_errores_tipos, revisor_tipos.tabla


def test_programa_valido() -> None:
    es_valido, lista_errores, tabla = compilar_hasta_semantico(
        "{ int a = 1; bool b = true; }"
    )

    assert es_valido
    assert lista_errores == ["Semantic OK"]
    assert tabla == {"a": "int", "b": "bool"}


def test_error_tipos_en_declaracion() -> None:
    es_valido, lista_errores, _ = compilar_hasta_semantico("{ int x = true; }")

    assert not es_valido
    assert lista_errores == [
        "Línea 1: ERROR DE TIPOS: La variable 'x' es int, pero se recibió bool."
    ]


def test_error_variable_no_declarada() -> None:
    es_valido, lista_errores, _ = compilar_hasta_semantico("{ x = 10; }")

    assert not es_valido
    assert lista_errores == [
        "Línea 1: ERROR DE DECLARACIÓN: La variable 'x' no ha sido declarada."
    ]


def test_error_variable_ya_declarada() -> None:
    es_valido, lista_errores, _ = compilar_hasta_semantico("{ int x = 1; int x = 2; }")

    assert not es_valido
    assert lista_errores == [
        "Línea 1: ERROR DE DECLARACIÓN: La variable 'x' ya fue declarada."
    ]


def test_codigo_intermedio_tabla_3_campos() -> None:
    fuente = "{ int contador = 1; bool activo = true; }"

    lista_tokens, _ = analizar_lexico(fuente)

    _, _, tabla = compilar_hasta_semantico(fuente)

    filas = generar_codigo_intermedio(tabla, lista_tokens)

    assert filas == [
        ("", "TITLE", "Pyngo"),
        ("", ".MODEL", "Small"),
        ("", ".486", ""),
        ("", ".STACK", ""),
        ("", "", ""),
        ("", ".DATA", ""),
        ("contador", "DW", "?"),
        ("activo", "DB", "?"),
        ("", "", ""),
        ("", ".CODE", ""),
        ("MAIN", "PROC", "FAR"),
        ("", ".STARTUP", ""),
        ("", "", ""),
        ("", "MOV", "AX, 1"),
        ("", "MOV", "contador, AX"),
        ("", "MOV", "AX, 1"),
        ("", "MOV", "activo, AL"),
        ("", "", ""),
        ("", ".EXIT", ""),
        ("MAIN", "ENDP", ""),
        ("", "", ""),
        ("", "END", ""),
    ]


def _filas_print(valor: int) -> list[tuple[str, str, str]]:
    fuente = "{ int x = " + str(valor) + "; print ( x ); }"

    lista_tokens, _ = analizar_lexico(fuente)

    _, _, tabla = compilar_hasta_semantico(fuente)

    return generar_codigo_intermedio(tabla, lista_tokens)


def test_print_codigo_3() -> None:
    filas = _filas_print(3)

    assert ("", "MOV", "AX, 3") in filas
    assert ("", "MOV", "AX, x") in filas

    # Caso cero imprime '0' (48).
    assert ("", "MOV", "DL, 48") in filas

    # División entre 10.
    assert ("", "MOV", "BX, 10") in filas
    assert ("", "MOV", "DX, 0") in filas
    assert ("", "DIV", "BX") in filas
    assert ("", "PUSH", "DX") in filas
    assert ("", "INC", "CX") in filas

    # Conversión a ASCII e impresión.
    assert ("", "POP", "DX") in filas
    assert ("", "ADD", "DL, 48") in filas
    assert ("", "MOV", "AH, 02H") in filas
    assert ("", "INT", "21H") in filas

    # LOOP para imprimir todos los dígitos.
    assert any(f[1] == "LOOP" for f in filas)

    # Orden: POP -> ADD DL,48 -> INT 21H.
    idx_pop = [i for i, f in enumerate(filas) if f == ("", "POP", "DX")][0]
    idx_add = [i for i, f in enumerate(filas) if f == ("", "ADD", "DL, 48")][0]
    # INT 21H de impresión: el que aparece después del POP.
    idx_int = [
        i for i, f in enumerate(filas) if f == ("", "INT", "21H") and i > idx_pop
    ][0]
    assert idx_pop < idx_add < idx_int

    # Sin variables COC/RESI.
    assert all(nombre not in ("COC", "RESI") for nombre, _, _ in filas)


def test_print_codigo_42() -> None:
    filas = _filas_print(42)

    assert ("", "MOV", "AX, 42") in filas
    assert ("", "MOV", "AX, x") in filas

    assert ("", "MOV", "BX, 10") in filas
    assert ("", "DIV", "BX") in filas
    assert ("", "PUSH", "DX") in filas
    assert ("", "POP", "DX") in filas
    assert ("", "ADD", "DL, 48") in filas
    assert ("", "MOV", "AH, 02H") in filas
    assert ("", "INT", "21H") in filas
    assert any(f[1] == "LOOP" for f in filas)

    idx_pop = [i for i, f in enumerate(filas) if f == ("", "POP", "DX")][0]
    idx_add = [i for i, f in enumerate(filas) if f == ("", "ADD", "DL, 48")][0]
    # INT 21H de impresión: el que aparece después del POP.
    idx_int = [
        i for i, f in enumerate(filas) if f == ("", "INT", "21H") and i > idx_pop
    ][0]
    assert idx_pop < idx_add < idx_int


def test_print_codigo_12345() -> None:
    filas = _filas_print(12345)

    assert ("", "MOV", "AX, 12345") in filas
    assert ("", "MOV", "AX, x") in filas

    assert ("", "MOV", "BX, 10") in filas
    assert ("", "DIV", "BX") in filas
    assert ("", "PUSH", "DX") in filas
    assert ("", "POP", "DX") in filas
    assert ("", "ADD", "DL, 48") in filas
    assert ("", "MOV", "AH, 02H") in filas
    assert ("", "INT", "21H") in filas
    assert any(f[1] == "LOOP" for f in filas)

    idx_pop = [i for i, f in enumerate(filas) if f == ("", "POP", "DX")][0]
    idx_add = [i for i, f in enumerate(filas) if f == ("", "ADD", "DL, 48")][0]
    # INT 21H de impresión: el que aparece después del POP.
    idx_int = [
        i for i, f in enumerate(filas) if f == ("", "INT", "21H") and i > idx_pop
    ][0]
    assert idx_pop < idx_add < idx_int


def _filas(fuente: str) -> list[tuple[str, str, str]]:
    lista_tokens, _ = analizar_lexico(fuente)

    _, _, tabla = compilar_hasta_semantico(fuente)

    return generar_codigo_intermedio(tabla, lista_tokens)


def test_intermedio_cuatro_operadores() -> None:
    filas = _filas(
        "{ int a = 1; int b = 2; int c = a @ b; int d = a # b; "
        "int e = a & b; int f = a | b; }"
    )

    # @ -> ADD, # -> SUB.
    assert ("", "ADD", "AX, b") in filas
    assert ("", "SUB", "AX, b") in filas

    # & -> MUL, | -> DIV (el operando pasa por BX y DX se limpia antes).
    assert ("", "MOV", "BX, b") in filas
    assert ("", "MUL", "BX") in filas
    assert ("", "MOV", "DX, 0") in filas
    assert ("", "DIV", "BX") in filas


def test_intermedio_if_con_etiquetas() -> None:
    filas = _filas(
        "{ int a = 1; int b = 2; int m = 0; if (a < b) { m = b; } else { m = a; }; }"
    )

    # Condición: MOV AX, a / CMP AX, b / salto si falso (a < b -> JGE).
    assert ("", "CMP", "AX, b") in filas
    assert ("", "JGE", "ETQ1") in filas

    # Rama verdadera, salto al fin, etiqueta else, rama falsa, etiqueta fin.
    assert ("", "MOV", "m, AX") in filas
    assert ("", "JMP", "ETQ2") in filas
    assert ("ETQ1:", "", "") in filas
    assert ("ETQ2:", "", "") in filas

    # El salto condicional va antes de la rama verdadera, y el else antes del fin.
    idx_cmp = filas.index(("", "CMP", "AX, b"))
    idx_salto = filas.index(("", "JGE", "ETQ1"))
    idx_verdad = filas.index(("", "MOV", "AX, b"))
    idx_else = filas.index(("ETQ1:", "", ""))
    idx_fin = filas.index(("ETQ2:", "", ""))
    assert idx_cmp < idx_salto < idx_verdad < idx_else < idx_fin
