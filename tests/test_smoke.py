"""Humo del compilador: casos que siempre deben pasar.

Se corre con:  pytest tests/ -q
"""

import os
import sys

import pytest

# Los tests importan el backend por ruta explícita a propósito:
# así no hay que convertir backend/ en paquete ni tocar app.py.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "backend"),
)

from intermedio import ErrorIntermedio, generar_codigo_intermedio
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


def test_intermedio_while_con_etiquetas() -> None:
    filas = _filas("{ int i = 0; while (i < 3) { i = i @ 1; }; }")

    # El while prueba la condición al inicio y repite mientras sea cierta.
    assert ("ETQ1:", "", "") in filas
    assert ("", "CMP", "AX, 3") in filas
    assert ("", "JGE", "ETQ2") in filas

    # Cuerpo y salto de vuelta al inicio.
    assert ("", "ADD", "AX, 1") in filas
    assert ("", "JMP", "ETQ1") in filas
    assert ("ETQ2:", "", "") in filas

    idx_inicio = filas.index(("ETQ1:", "", ""))
    idx_cmp = filas.index(("", "CMP", "AX, 3"))
    idx_salto = filas.index(("", "JGE", "ETQ2"))
    idx_vuelta = filas.index(("", "JMP", "ETQ1"))
    idx_fin = filas.index(("ETQ2:", "", ""))
    assert idx_inicio < idx_cmp < idx_salto < idx_vuelta < idx_fin


def test_error_tipo_en_while() -> None:
    es_valido, lista_errores, _ = compilar_hasta_semantico(
        "{ int a = 1; while (a) { a = 1; }; }"
    )

    assert not es_valido
    assert lista_errores == [
        "Línea 1: ERROR DE TIPOS: La condición del while debe ser bool."
    ]


def test_intermedio_cadena_suma_y_resta() -> None:
    filas = _filas("{ int a = 1; int b = 2; int c = 3; int d = a @ b # c; }")

    # @ y # tienen el mismo nivel: se encadenan de izquierda a derecha.
    idx_carga = filas.index(("", "MOV", "AX, a"))
    idx_suma = filas.index(("", "ADD", "AX, b"))
    idx_resta = filas.index(("", "SUB", "AX, c"))
    assert idx_carga < idx_suma < idx_resta
    assert ("", "MOV", "d, AX") in filas


def test_intermedio_cadena_producto() -> None:
    filas = _filas("{ int a = 1; int b = 2; int c = 3; int d = a & b & c; }")

    assert filas.count(("", "MUL", "BX")) == 2
    assert ("", "MOV", "d, AX") in filas


def test_intermedio_rechaza_expresion_anidada() -> None:
    fuente = "{ int a = 1; int b = 2; int c = 3; int d = a @ b & c; }"

    lista_tokens, _ = analizar_lexico(fuente)

    _, _, tabla = compilar_hasta_semantico(fuente)

    with pytest.raises(ErrorIntermedio):
        generar_codigo_intermedio(tabla, lista_tokens)


def test_intermedio_rechaza_parentesis() -> None:
    fuente = "{ int a = 1; int b = 2; int c = ( a @ b ); }"

    lista_tokens, _ = analizar_lexico(fuente)

    _, _, tabla = compilar_hasta_semantico(fuente)

    with pytest.raises(ErrorIntermedio):
        generar_codigo_intermedio(tabla, lista_tokens)


def test_intermedio_rechaza_comparacion_compuesta() -> None:
    fuente = "{ int a = 1; int b = 2; int c = 3; if (a < b @ c) { a = 1; }; }"

    lista_tokens, _ = analizar_lexico(fuente)

    _, _, tabla = compilar_hasta_semantico(fuente)

    with pytest.raises(ErrorIntermedio):
        generar_codigo_intermedio(tabla, lista_tokens)


def test_scanner_rechaza_identificadores_no_ascii() -> None:
    for fuente, esperado in (
        ("{ int A = 1; }", "Línea 1: Caracter inválido 'A'."),
        ("{ int ñ = 1; }", "Línea 1: Caracter inválido 'ñ'."),
        ("{ int añ = 1; }", "Línea 1: Caracter inválido 'ñ'."),
        ("{ int a² = 1; }", "Línea 1: Caracter inválido '²'."),
    ):
        _, lista_errores = analizar_lexico(fuente)

        assert lista_errores == [esperado], fuente


def test_scanner_acepta_minusculas_y_digitos() -> None:
    lista_tokens, lista_errores = analizar_lexico("{ int contador1 = 1; }")

    assert lista_errores == []
    assert any(token.lexeme == "contador1" for token in lista_tokens)
