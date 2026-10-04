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


def compilar(codigo):
    """Corre scanner → parser → semántico y devuelve (ok, errores, tabla)."""
    tokens, lexicos = analizar_lexico(codigo)

    assert lexicos == []

    parser = Parser(tokens)
    ok, sintacticos = parser.analizar()

    assert ok, sintacticos

    semantico = AnalizadorSemantico(tokens)
    ok, semanticos = semantico.analizar()

    return ok, semanticos, semantico.tabla


def test_programa_valido():
    ok, errores, tabla = compilar("{ int a = 1; bool b = true; }")

    assert ok
    assert errores == ["Semantic OK"]
    assert tabla == {"a": "int", "b": "bool"}


def test_error_tipos_en_declaracion():
    ok, errores, _ = compilar("{ int x = true; }")

    assert not ok
    assert errores == [
        "Línea 1: ERROR DE TIPOS: La variable 'x' es int, pero se recibió bool."
    ]


def test_error_variable_no_declarada():
    ok, errores, _ = compilar("{ x = 10; }")

    assert not ok
    assert errores == [
        "Línea 1: ERROR DE DECLARACIÓN: La variable 'x' no ha sido declarada."
    ]


def test_error_variable_ya_declarada():
    ok, errores, _ = compilar("{ int x = 1; int x = 2; }")

    assert not ok
    assert errores == [
        "Línea 1: ERROR DE DECLARACIÓN: La variable 'x' ya fue declarada."
    ]


def test_intermedio_solo_directivas():
    _, _, tabla = compilar("{ int contador = 1; bool activo = true; }")

    assert generar_codigo_intermedio(tabla) == ("contador DW ?\nactivo DB ?")
