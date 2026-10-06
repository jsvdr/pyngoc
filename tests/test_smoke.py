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


def test_intermedio_solo_directivas() -> None:
    _, _, tabla = compilar_hasta_semantico("{ int contador = 1; bool activo = true; }")

    assert generar_codigo_intermedio(tabla) == ("contador DW ?\nactivo DB ?")
