# Objeto: tokens + tabla -> código máquina x86 de 16 bits.
#
# Igual que intermedio.py, no hay árbol: se recorren los tokens copiando la
# forma del parser. Cada expresión deja su resultado en AX.
#
# El programa se arma en dos pasadas:
#   1. Se calculan las direcciones suponiendo saltos cortos.
#   2. Si algún salto no entra en -128..127, se pasa a cercano y se repite.
# Al final se codifican los bytes y se formatean para el panel.

from typing import TypeAlias, TypedDict

from codificador import (
    ErrorCodificador,
    Operando,
    codificar,
    codificar_salto,
    tamano_salto,
)
from tokens import Token, TokenKind

DATA_BASE = 0x2000
CODE_BASE = 0x0000

BYTES_POR_VARIABLE = 2


class ErrorObjeto(Exception):
    """Algo que esta fase no puede generar."""


class Fila(TypedDict):
    direccion: int
    bytes: list[int]
    texto: str


class FilaPanel(TypedDict):
    direccion: str
    contenido: str
    hex: str
    texto: str


class Etiqueta:
    def __init__(self, nombre: str) -> None:
        self.nombre = nombre


class Instruccion:
    def __init__(
        self,
        mnemonico: str,
        operandos: tuple[Operando, ...],
        forzar: str | None,
        texto: str,
    ) -> None:
        self.mnemonico = mnemonico
        self.operandos = operandos
        self.forzar = forzar
        self.texto = texto


class Salto:
    def __init__(self, mnemonico: str, etiqueta: str) -> None:
        self.mnemonico = mnemonico
        self.etiqueta = etiqueta
        # CALL no tiene versión corta.
        self.corto = mnemonico != "CALL"


# Un elemento del programa: etiqueta, instrucción o salto a resolver.
Item: TypeAlias = Etiqueta | Instruccion | Salto


class GeneradorObjeto:
    tokens: list[Token]
    posicion: int
    tabla: dict[str, str]
    direcciones: dict[str, int]
    items: list[Item]
    errores: list[str]
    numero_etiqueta: int

    def __init__(self, tokens: list[Token], tabla: dict[str, str]) -> None:
        self.tokens = tokens
        self.posicion = 0
        self.tabla = tabla
        self.errores = []
        self.numero_etiqueta = 0

        # Las variables van en orden de declaración: 2000h, 2002h, ...
        self.direcciones = {}

        for posicion, nombre in enumerate(tabla):
            self.direcciones[nombre] = DATA_BASE + BYTES_POR_VARIABLE * posicion

        self.items: list[Item] = []

    def generar(self) -> tuple[list[Item], list[str]]:
        self.programa()

        if not self.token_actual_es(TokenKind.EOF):
            self.anotar_error(self.token_actual().line, "Se esperaba el final.")

        # Fin del programa y rutina de impresión (por ahora solo RET).
        self.emitir("HLT", ())
        self.etiqueta("rutina_print")
        self.emitir("RET", ())

        return self.items, self.errores

    # PROGRAMA → { LISTA_DECL }
    def programa(self) -> None:
        self.avanzar_si_es(TokenKind.LBRACE)

        self.lista_decl()

        self.avanzar_si_es(TokenKind.RBRACE)

    # LISTA_DECL → [ DECL ; ]*
    def lista_decl(self) -> None:
        while not self.token_actual_es(TokenKind.RBRACE) and not self.token_actual_es(
            TokenKind.EOF
        ):
            self.decl()

            self.avanzar_si_es(TokenKind.SEMICOLON)

    # DECL → DECL_VAR | ASIGNACION | IF | WHILE | PRINT
    def decl(self) -> None:
        if self.token_actual_es(TokenKind.INT) or self.token_actual_es(TokenKind.BOOL):
            self.decl_var()
            return

        if self.token_actual_es(TokenKind.ID):
            self.asignacion()
            return

        if self.token_actual_es(TokenKind.IF):
            self.if_stmt()
            return

        if self.token_actual_es(TokenKind.WHILE):
            self.while_stmt()
            return

        if self.token_actual_es(TokenKind.PRINT):
            self.print_stmt()
            return

        self.avanzar()

    # DECL_VAR → TIPO_DATO ID = EXPRESION
    def decl_var(self) -> None:
        numero_linea = self.token_actual().line

        self.tipo_dato()

        nombre_variable = self.token_actual().lexeme

        self.avanzar_si_es(TokenKind.ID)
        self.avanzar_si_es(TokenKind.ASSIGN)

        self.expresion()

        self.guardar_en_variable(nombre_variable, numero_linea)

    # ASIGNACION → ID = EXPRESION
    def asignacion(self) -> None:
        numero_linea = self.token_actual().line

        nombre_variable = self.token_actual().lexeme

        self.avanzar_si_es(TokenKind.ID)
        self.avanzar_si_es(TokenKind.ASSIGN)

        self.expresion()

        self.guardar_en_variable(nombre_variable, numero_linea)

    # El resultado de la expresión está en AX: se guarda en la variable.
    def guardar_en_variable(self, nombre_variable: str, numero_linea: int) -> None:
        if nombre_variable not in self.direcciones:
            self.anotar_error(
                numero_linea,
                f"La variable '{nombre_variable}' no ha sido declarada.",
            )
            return

        direccion = self.direcciones[nombre_variable]

        self.emitir("MOV", (("mem", direccion), ("reg", "AX")))

    # IF → if EXPRESION { LISTA_DECL } [ else { LISTA_DECL } ]
    def if_stmt(self) -> None:
        self.avanzar_si_es(TokenKind.IF)

        # Los paréntesis de la condición, si los hay, los consume FACTOR.
        self.expresion()

        self.avanzar_si_es(TokenKind.LBRACE)

        etiqueta_else = self.nueva_etiqueta("IF_ELSE")
        etiqueta_fin = self.nueva_etiqueta("IF_FIN")

        # Si la condición dio 0, salta al else (o al fin).
        self.emitir("CMP", (("reg", "AX"), ("imm", 0)))
        self.salto("JE", etiqueta_else)

        self.lista_decl()

        self.avanzar_si_es(TokenKind.RBRACE)

        if self.token_actual_es(TokenKind.ELSE):
            self.salto("JMP", etiqueta_fin)
            self.etiqueta(etiqueta_else)

            self.avanzar_si_es(TokenKind.ELSE)
            self.avanzar_si_es(TokenKind.LBRACE)

            self.lista_decl()

            self.avanzar_si_es(TokenKind.RBRACE)

            self.etiqueta(etiqueta_fin)
            return

        self.etiqueta(etiqueta_else)

    # WHILE → while EXPRESION { LISTA_DECL }
    # Prueba la condición antes de cada vuelta: si sigue siendo cierta, repite.
    def while_stmt(self) -> None:
        etiqueta_inicio = self.nueva_etiqueta("WHILE_INICIO")
        etiqueta_fin = self.nueva_etiqueta("WHILE_FIN")

        self.etiqueta(etiqueta_inicio)

        self.avanzar_si_es(TokenKind.WHILE)

        # Igual que en if: los paréntesis son parte de la expresión.
        self.expresion()

        self.avanzar_si_es(TokenKind.LBRACE)

        self.emitir("CMP", (("reg", "AX"), ("imm", 0)))
        self.salto("JE", etiqueta_fin)

        self.lista_decl()

        self.avanzar_si_es(TokenKind.RBRACE)

        # Vuelve al inicio para volver a probar la condición.
        self.salto("JMP", etiqueta_inicio)
        self.etiqueta(etiqueta_fin)

    # PRINT → print ( EXPRESION )
    def print_stmt(self) -> None:
        self.avanzar_si_es(TokenKind.PRINT)
        self.avanzar_si_es(TokenKind.LPAREN)

        self.expresion()

        self.avanzar_si_es(TokenKind.RPAREN)

        self.emitir("PUSH", (("reg", "AX"),))
        self.salto("CALL", "rutina_print")
        self.emitir("ADD", (("reg", "SP"), ("imm", 2)), forzar="imm8")

    # EXPRESION → SUMA [ ( == | > | < ) SUMA ]*
    # Deja 0 o 1 en AX cuando hay comparación.
    def expresion(self) -> None:
        self.suma()

        while (
            self.token_actual_es(TokenKind.EQ)
            or self.token_actual_es(TokenKind.GREATER)
            or self.token_actual_es(TokenKind.LESS)
        ):
            mnemonico_salto = self.mnemonico_de_comparacion()

            self.avanzar()

            etiqueta_verdadero = self.nueva_etiqueta("CMP_VERDADERO")
            etiqueta_fin = self.nueva_etiqueta("CMP_FIN")

            self.comparar_con_derecha()

            self.salto(mnemonico_salto, etiqueta_verdadero)
            self.emitir("MOV", (("reg", "AX"), ("imm", 0)))
            self.salto("JMP", etiqueta_fin)
            self.etiqueta(etiqueta_verdadero)
            self.emitir("MOV", (("reg", "AX"), ("imm", 1)))
            self.etiqueta(etiqueta_fin)

    def mnemonico_de_comparacion(self) -> str:
        if self.token_actual_es(TokenKind.EQ):
            return "JE"

        if self.token_actual_es(TokenKind.GREATER):
            return "JA"

        return "JB"

    # CMP AX, lado derecho. La izquierda ya está en AX.
    def comparar_con_derecha(self) -> None:
        if self.es_suma_simple():
            derecha = self.operando()
            self.emitir("CMP", (("reg", "AX"), self.fuente_de(derecha)))
            return

        self.emitir("PUSH", (("reg", "AX"),))
        self.suma()
        self.emitir("MOV", (("reg", "BX"), ("reg", "AX")))
        self.emitir("POP", (("reg", "AX"),))
        self.emitir("CMP", (("reg", "AX"), ("reg", "BX")))

    # SUMA → TERMINO [ ( @ | # ) TERMINO ]*
    def suma(self) -> None:
        self.termino()

        while self.token_actual_es(TokenKind.AT) or self.token_actual_es(
            TokenKind.HASH
        ):
            mnemonico = "ADD" if self.token_actual_es(TokenKind.AT) else "SUB"

            self.avanzar()

            if self.es_termino_simple():
                derecha = self.operando()
                self.emitir(mnemonico, (("reg", "AX"), self.fuente_de(derecha)))
            else:
                # El lado derecho es compuesto: se guarda AX en la pila.
                self.emitir("PUSH", (("reg", "AX"),))
                self.termino()
                self.emitir("MOV", (("reg", "BX"), ("reg", "AX")))
                self.emitir("POP", (("reg", "AX"),))
                self.emitir(mnemonico, (("reg", "AX"), ("reg", "BX")))

    # TERMINO → FACTOR [ ( & | | ) FACTOR ]*
    def termino(self) -> None:
        if self.token_actual_es(TokenKind.LPAREN):
            self.factor()
        else:
            izquierda = self.operando()
            self.cargar_en_ax(izquierda)

        while self.token_actual_es(TokenKind.AMPERSAND) or self.token_actual_es(
            TokenKind.PIPE
        ):
            mnemonico = "MUL" if self.token_actual_es(TokenKind.AMPERSAND) else "DIV"

            self.avanzar()

            if self.es_factor_simple():
                derecha = self.operando()
                self.emitir_mul_div(mnemonico, derecha)
            else:
                # Se evalúa el factor derecho y se deja en BX.
                self.emitir("PUSH", (("reg", "AX"),))
                self.factor()
                self.emitir("MOV", (("reg", "BX"), ("reg", "AX")))
                self.emitir("POP", (("reg", "AX"),))

                if mnemonico == "DIV":
                    self.emitir("MOV", (("reg", "DX"), ("imm", 0)))

                self.emitir(mnemonico, (("reg", "BX"),))

    # MUL/DIV con el lado derecho simple (variable o número).
    def emitir_mul_div(self, mnemonico: str, derecha: Operando) -> None:
        if derecha[0] == "id":
            if derecha[1] not in self.direcciones:
                raise ErrorObjeto(
                    f"La variable '{derecha[1]}' no ha sido declarada.",
                )

            if mnemonico == "DIV":
                self.emitir("MOV", (("reg", "DX"), ("imm", 0)))

            direccion = self.direcciones[derecha[1]]
            self.emitir(mnemonico, (("mem", direccion),))
            return

        if derecha[0] != "num" and derecha[0] != "bool":
            raise ErrorObjeto("MUL y DIV necesitan una variable o un número.")

        # MUL/DIV no aceptan inmediato: se pasa por BX.
        self.emitir("MOV", (("reg", "BX"), ("imm", derecha[1])))

        if mnemonico == "DIV":
            self.emitir("MOV", (("reg", "DX"), ("imm", 0)))

        self.emitir(mnemonico, (("reg", "BX"),))

    # FACTOR → ID | NUM | BOOL | ( EXPRESION )
    def factor(self) -> None:
        # ID: se lee de su dirección directa.
        if self.token_actual_es(TokenKind.ID):
            nombre_variable = self.token_actual().lexeme
            numero_linea = self.token_actual().line

            self.avanzar()

            if nombre_variable not in self.direcciones:
                self.anotar_error(
                    numero_linea,
                    f"La variable '{nombre_variable}' no ha sido declarada.",
                )
                return

            self.cargar_en_ax(("id", nombre_variable))
            return

        # NUM
        if self.token_actual_es(TokenKind.NUM):
            numero_linea = self.token_actual().line
            valor = int(self.token_actual().lexeme)

            self.avanzar()

            self.validar_numero(valor, numero_linea)
            self.cargar_en_ax(("num", valor))
            return

        # true = 1, false = 0
        if self.token_actual_es(TokenKind.TRUE) or self.token_actual_es(
            TokenKind.FALSE
        ):
            valor = 1 if self.token_actual_es(TokenKind.TRUE) else 0

            self.avanzar()

            self.cargar_en_ax(("bool", valor))
            return

        # ( EXPRESION ): cambia el orden, no el resultado.
        if self.token_actual_es(TokenKind.LPAREN):
            self.avanzar()

            self.expresion()

            self.avanzar_si_es(TokenKind.RPAREN)
            return

        numero_linea = self.token_actual().line

        self.anotar_error(numero_linea, "Se esperaba una expresión.")
        self.avanzar()

    # OPERANDO → ID | NUM | true | false   (sin emitir nada)
    def operando(self) -> Operando:
        token = self.token_actual()

        if token.kind == TokenKind.TRUE:
            self.avanzar()
            return ("bool", 1)

        if token.kind == TokenKind.FALSE:
            self.avanzar()
            return ("bool", 0)

        if token.kind == TokenKind.NUM:
            self.avanzar()
            self.validar_numero(int(token.lexeme), token.line)
            return ("num", int(token.lexeme))

        if token.kind == TokenKind.ID:
            self.avanzar()

            if token.lexeme not in self.direcciones:
                self.anotar_error(
                    token.line,
                    f"La variable '{token.lexeme}' no ha sido declarada.",
                )

            return ("id", token.lexeme)

        self.anotar_error(token.line, "Se esperaba una variable o un número.")
        self.avanzar()

        return ("num", 0)

    # Un operando simple se convierte en fuente de instrucción.
    def fuente_de(self, operando: Operando) -> Operando:
        if operando[0] == "id":
            if operando[1] not in self.direcciones:
                raise ErrorObjeto(
                    f"La variable '{operando[1]}' no ha sido declarada.",
                )

            return ("mem", self.direcciones[operando[1]])

        if operando[0] == "num" or operando[0] == "bool":
            return ("imm", operando[1])

        raise ErrorObjeto(f"No se puede usar {operando} como fuente.")

    def cargar_en_ax(self, operando: Operando) -> None:
        self.emitir("MOV", (("reg", "AX"), self.fuente_de(operando)))

    # ¿El próximo TERMINO es un solo operando, sin & ni |?
    def es_termino_simple(self) -> bool:
        if self.token_actual_es(TokenKind.LPAREN):
            return False

        siguiente = self.posicion + 1

        if siguiente < len(self.tokens):
            return self.tokens[siguiente].kind not in (
                TokenKind.AMPERSAND,
                TokenKind.PIPE,
            )

        return True

    # ¿La próxima SUMA es un solo operando? Acá también cuentan @ y #.
    def es_suma_simple(self) -> bool:
        if self.token_actual_es(TokenKind.LPAREN):
            return False

        siguiente = self.posicion + 1

        if siguiente < len(self.tokens):
            return self.tokens[siguiente].kind not in (
                TokenKind.AT,
                TokenKind.HASH,
                TokenKind.AMPERSAND,
                TokenKind.PIPE,
            )

        return True

    # ¿El próximo FACTOR es simple? Solo el paréntesis arma algo compuesto.
    def es_factor_simple(self) -> bool:
        return not self.token_actual_es(TokenKind.LPAREN)

    def validar_numero(self, valor: int, numero_linea: int) -> None:
        if valor > 0xFFFF:
            self.anotar_error(
                numero_linea,
                f"El número {valor} no entra en 16 bits (0..65535).",
            )

    def tipo_dato(self) -> None:
        if self.token_actual_es(TokenKind.INT) or self.token_actual_es(TokenKind.BOOL):
            self.avanzar()

    # ==================================
    # EMISIÓN
    # ==================================

    def emitir(
        self,
        mnemonico: str,
        operandos: tuple[Operando, ...],
        forzar: str | None = None,
    ) -> None:
        texto = self.texto_de(mnemonico, operandos)
        self.items.append(Instruccion(mnemonico, operandos, forzar, texto))

    def salto(self, mnemonico: str, etiqueta: str) -> None:
        self.items.append(Salto(mnemonico, etiqueta))

    def etiqueta(self, nombre: str) -> None:
        self.items.append(Etiqueta(nombre))

    def nueva_etiqueta(self, prefijo: str) -> str:
        self.numero_etiqueta += 1
        return f"{prefijo}_{self.numero_etiqueta}"

    # Texto legible para el tooltip del panel.
    def texto_de(self, mnemonico: str, operandos: tuple[Operando, ...]) -> str:
        if len(operandos) == 0:
            return mnemonico

        partes = [self.texto_de_operando(operando) for operando in operandos]

        return f"{mnemonico} " + ", ".join(partes)

    def texto_de_operando(self, operando: Operando) -> str:
        if operando[0] == "reg":
            return operando[1]

        if operando[0] == "imm":
            return str(operando[1])

        if len(operando) == 2:
            return f"[{operando[1]:04X}h]"

        return f"[{operando[1]}{operando[2]:+d}]"

    def anotar_error(self, numero_linea: int, texto_error: str) -> None:
        self.errores.append(
            f"Línea {numero_linea}: ERROR DE CÓDIGO OBJETO: {texto_error}",
        )

    def avanzar_si_es(self, kind_esperado: TokenKind) -> None:
        if self.token_actual_es(kind_esperado):
            self.avanzar()

    def token_actual_es(self, kind_esperado: TokenKind) -> bool:
        return self.token_actual().kind == kind_esperado

    def token_actual(self) -> Token:
        return self.tokens[self.posicion]

    def avanzar(self) -> None:
        if self.posicion < len(self.tokens) - 1:
            self.posicion += 1


# ==================================
# ARMADO EN DOS PASADAS
# ==================================


def tamano_de(item: Item) -> int:
    if isinstance(item, Etiqueta):
        return 0

    if isinstance(item, Salto):
        return tamano_salto(item.mnemonico, item.corto)

    return len(codificar(item.mnemonico, item.operandos, item.forzar))


# Devuelve una fila por instrucción: dirección, bytes y texto.
def ensamblar(items: list[Item]) -> list[Fila]:
    direcciones: dict[str, int] = {}
    posiciones: list[int] = []

    # Se repite hasta que ningún salto corto quede fuera de rango.
    for _ in range(len(items) + 2):
        direcciones = {}
        posiciones = []
        direccion = CODE_BASE

        for item in items:
            posiciones.append(direccion)

            if isinstance(item, Etiqueta):
                direcciones[item.nombre] = direccion
            else:
                direccion += tamano_de(item)

        promovido = False

        for posicion, item in enumerate(items):
            if not isinstance(item, Salto) or not item.corto:
                continue

            if item.etiqueta not in direcciones:
                raise ErrorObjeto(f"No existe la etiqueta '{item.etiqueta}'.")

            siguiente = posiciones[posicion] + tamano_salto(item.mnemonico, True)
            relativo = direcciones[item.etiqueta] - siguiente

            if not -128 <= relativo <= 127:
                item.corto = False
                promovido = True

        if not promovido:
            break

    filas: list[Fila] = []

    for posicion, item in enumerate(items):
        if isinstance(item, Etiqueta):
            continue

        if isinstance(item, Salto):
            if item.etiqueta not in direcciones:
                raise ErrorObjeto(f"No existe la etiqueta '{item.etiqueta}'.")

            siguiente = posiciones[posicion] + tamano_salto(
                item.mnemonico,
                item.corto,
            )
            relativo = direcciones[item.etiqueta] - siguiente
            bytes_instruccion = codificar_salto(
                item.mnemonico,
                relativo,
                item.corto,
            )
            texto = f"{item.mnemonico} {item.etiqueta}"
        else:
            bytes_instruccion = codificar(
                item.mnemonico,
                item.operandos,
                item.forzar,
            )
            texto = item.texto

        filas.append(
            {
                "direccion": posiciones[posicion],
                "bytes": bytes_instruccion,
                "texto": texto,
            },
        )

    return filas


# ==================================
# FORMATO PARA EL PANEL
# ==================================


# DIR en binario: 16 bits en cuatro nibbles, un espacio entre cada uno.
def formatear_direccion(direccion: int) -> str:
    return " ".join(
        f"{(direccion >> desplazamiento) & 0xF:04b}" for desplazamiento in (12, 8, 4, 0)
    )


# CONTENIDO: dos nibbles por byte (un espacio) y dos espacios entre bytes.
def formatear_binario(bytes_instruccion: list[int]) -> str:
    partes: list[str] = []

    for byte in bytes_instruccion:
        partes.append(f"{byte >> 4:04b} {byte & 0x0F:04b}")

    return "  ".join(partes)


def formatear_hex(bytes_instruccion: list[int]) -> str:
    return " ".join(f"{byte:02X}" for byte in bytes_instruccion)


def fila_para_panel(fila: Fila) -> FilaPanel:
    return {
        "direccion": formatear_direccion(fila["direccion"]),
        "contenido": formatear_binario(fila["bytes"]),
        "hex": formatear_hex(fila["bytes"]),
        "texto": fila["texto"],
    }


def filas_de_datos(tabla: dict[str, str]) -> list[FilaPanel]:
    filas: list[FilaPanel] = []

    for posicion, (nombre, tipo) in enumerate(tabla.items()):
        filas.append(
            {
                "direccion": formatear_direccion(
                    DATA_BASE + BYTES_POR_VARIABLE * posicion,
                ),
                "contenido": formatear_binario([0x00, 0x00]),
                "hex": formatear_hex([0x00, 0x00]),
                "texto": f"{nombre} : {tipo}",
            },
        )

    return filas


# ==================================
# ENTRADA DE LA FASE
# ==================================


def generar_codigo_objeto(
    tokens: list[Token],
    tabla: dict[str, str],
) -> tuple[bool, list[FilaPanel], list[FilaPanel], list[str]]:
    generador = GeneradorObjeto(tokens, tabla)

    try:
        items, errores = generador.generar()

        if len(errores) > 0:
            return False, [], [], errores

        filas = ensamblar(items)
    except (ErrorObjeto, ErrorCodificador) as error:
        return False, [], [], [str(error)]

    datos = filas_de_datos(tabla)
    codigo = [fila_para_panel(fila) for fila in filas]

    return True, datos, codigo, ["Código Objeto OK"]
