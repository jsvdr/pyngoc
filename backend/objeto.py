# Objeto: tokens + tabla -> bytes x86 de 16 bits. Cada expresión deja su resultado en AX.
from collections import namedtuple
from typing import Any, TypeAlias

from codificador import ErrorCodificador, codificar, codificar_salto
from recorrido import Recorrido
from tokens import Token
from tokens import TokenKind as T

DATA_BASE = 0x0000  # DATOS y CÓDIGO son segmentos distintos: los dos empiezan en 0
CODE_BASE = 0x0000

AX, BX, DX, SP, AL, AH, DL = (("reg", r) for r in ("AX", "BX", "DX", "SP", "AL", "AH", "DL"))
COMPARACIONES = {T.EQ: "JE", T.GREATER: "JA", T.LESS: "JB"}  # sin signo: valores 0..65535
ARITMETICOS = (T.AT, T.HASH, T.AMPERSAND, T.PIPE)

Etiqueta = namedtuple("Etiqueta", "nombre")
Instruccion = namedtuple("Instruccion", "mnemonico operandos forzar texto")
Salto = namedtuple("Salto", "mnemonico etiqueta")

Fila: TypeAlias = dict[str, Any]
FilaPanel: TypeAlias = dict[str, str]


class ErrorObjeto(Exception):
    """Algo que esta fase no puede generar."""


def imm(valor: int) -> tuple:
    return ("imm", valor)


def mem(direccion: int) -> tuple:
    return ("mem", direccion)


def texto_de(operando: tuple) -> str:
    if operando[0] == "reg":
        return operando[1]
    if operando[0] == "imm":
        return str(operando[1])
    if len(operando) == 2:
        return f"[{operando[1]:04X}h]"
    return f"[{operando[1]}{operando[2]:+d}]"


class GeneradorObjeto(Recorrido):
    def __init__(self, tokens: list[Token], tabla: dict[str, str]) -> None:
        super().__init__(tokens)
        self.tabla = tabla
        self.direcciones: dict[str, int] = {}
        direccion = DATA_BASE
        for nombre, tipo in tabla.items():  # int: 2 bytes · bool: 1 byte
            self.direcciones[nombre] = direccion
            direccion += 1 if tipo == "bool" else 2
        self.tiene_print = any(token.kind == T.PRINT for token in tokens)
        if self.tiene_print:  # COC y RESI: 1 byte cada una, después de las variables
            self.direcciones["COC"], self.direcciones["RESI"] = direccion, direccion + 1
        self.items: list = []
        self.numero_etiqueta = 0

    def generar(self) -> list[tuple[int, list[int], str]]:
        self.bloque()
        self.emitir("HLT")
        if self.tiene_print:
            self.rutina_print()
        return ensamblar(self.items)

    # ---------- sentencias ----------

    def bloque(self) -> None:  # { LISTA_DECL }: sirve para el programa, if, else y while
        self.avanzar_si_es(T.LBRACE)
        while not self.token_actual_es(T.RBRACE) and not self.token_actual_es(T.EOF):
            self.decl()
            self.avanzar_si_es(T.SEMICOLON)
        self.avanzar_si_es(T.RBRACE)

    def decl(self) -> None:
        kind = self.token_actual().kind
        if kind == T.IF:
            self.if_stmt()
        elif kind == T.WHILE:
            self.while_stmt()
        elif kind == T.PRINT:
            self.print_stmt()
        else:
            self.asignacion()  # DECL_VAR y ASIGNACION generan lo mismo

    def asignacion(self) -> None:  # [int | bool] ID = EXPRESION
        if self.token_actual().kind in (T.INT, T.BOOL):
            self.avanzar()
        nombre = self.token_actual()
        self.avanzar()  # ID
        self.avanzar()  # =
        self.expresion()
        registro = AL if self.tabla.get(nombre.lexeme) == "bool" else AX  # bool = 1 byte
        self.emitir("MOV", mem(self.direccion_de(nombre)), registro)

    def condicion(self, etiqueta_falsa: str) -> None:  # si la expresión da 0 salta
        self.avanzar()  # if / while
        self.expresion()
        self.emitir("CMP", AX, imm(0))
        self.salto("JE", etiqueta_falsa)

    def if_stmt(self) -> None:
        falso = self.nueva_etiqueta("IF_FALSO")
        self.condicion(falso)
        self.bloque()
        self.etiqueta(falso)

    def while_stmt(self) -> None:
        inicio, fin = self.nueva_etiqueta("WHILE_INICIO"), self.nueva_etiqueta("WHILE_FIN")
        self.etiqueta(inicio)
        self.condicion(fin)
        self.bloque()
        self.salto("JMP", inicio)
        self.etiqueta(fin)

    def print_stmt(self) -> None:
        self.avanzar()  # print
        self.avanzar()  # (
        nombre = self.token_actual()
        self.avanzar()  # ID
        self.avanzar()  # )
        self.emitir("MOV", AX, mem(self.direccion_de(nombre)))
        self.emitir("PUSH", AX)
        self.salto("CALL", "rutina_print")
        self.emitir("ADD", SP, imm(2), forzar="imm8")

    def rutina_print(self) -> None:  # igual que el CI: DIV DL, COC, RESI, INT 21H
        coc, resi = self.direcciones["COC"], self.direcciones["RESI"]
        self.etiqueta("rutina_print")
        self.emitir("MOV", BX, SP)
        self.emitir("MOV", AX, ("mem", "BX", 2))
        self.emitir("MOV", DL, imm(10))
        self.emitir("DIV", DL)
        self.emitir("MOV", mem(coc), AL, texto="MOV COC, AL")
        self.emitir("MOV", mem(resi), AH, texto="MOV RESI, AH")
        for direccion, nombre in ((coc, "COC"), (resi, "RESI")):
            self.emitir("MOV", DL, mem(direccion), texto=f"MOV DL, {nombre}")
            self.emitir("ADD", DL, imm(0x30), texto="ADD DL, 30H")
            self.emitir("MOV", AH, imm(2), texto="MOV AH, 02H")
            self.emitir("INT", imm(0x21), texto="INT 21H")
        self.emitir("RET")

    # ---------- expresiones ----------

    def expresion(self) -> None:  # SUMA [ (== | > | <) SUMA ]: deja 0 ó 1 en AX
        self.suma()
        kind = self.token_actual().kind
        if kind in COMPARACIONES:
            self.avanzar()
            self.operar("CMP", self.suma)
            verdadero, fin = self.nueva_etiqueta("CMP_VERDADERO"), self.nueva_etiqueta("CMP_FIN")
            self.salto(COMPARACIONES[kind], verdadero)
            self.emitir("MOV", AX, imm(0))
            self.salto("JMP", fin)
            self.etiqueta(verdadero)
            self.emitir("MOV", AX, imm(1))
            self.etiqueta(fin)

    def suma(self) -> None:
        self.binaria({T.AT: "ADD", T.HASH: "SUB"}, self.termino)

    def termino(self) -> None:
        self.binaria({T.AMPERSAND: "MUL", T.PIPE: "DIV"}, self.factor)

    def binaria(self, operadores: dict, siguiente) -> None:  # siguiente [ operador siguiente ]*
        siguiente()
        while self.token_actual().kind in operadores:
            mnemonico = operadores[self.token_actual().kind]
            self.avanzar()
            self.operar(mnemonico, siguiente)

    def operar(self, mnemonico: str, derecha) -> None:
        """AX = AX <mnemonico> lado derecho. MUL y DIV trabajan con BX."""
        simple, mul_div = self.es_simple(), mnemonico in ("MUL", "DIV")
        if simple and not mul_div:
            self.emitir(mnemonico, AX, self.fuente())  # ADD AX,[x] · SUB AX,1 · CMP AX,5
            return
        if simple:
            self.emitir("MOV", BX, self.fuente())
        else:  # lado derecho compuesto (o bool): AX espera en la pila
            self.emitir("PUSH", AX)
            derecha()
            self.emitir("MOV", BX, AX)
            self.emitir("POP", AX)
        if mnemonico == "DIV":
            self.emitir("MOV", DX, imm(0))
        if mul_div:
            self.emitir(mnemonico, BX)
        else:
            self.emitir(mnemonico, AX, BX)

    def factor(self) -> None:  # ID | NUM | BOOL | ( EXPRESION )
        if self.token_actual_es(T.LPAREN):
            self.avanzar()
            self.expresion()
            self.avanzar()
            return
        token = self.token_actual()
        if token.kind in (T.TRUE, T.FALSE):
            self.emitir("MOV", AL, self.fuente())
            self.emitir("MOV", AH, imm(0))
        elif self.tabla.get(token.lexeme) == "bool":  # 1 byte: se carga en AL y AH queda en 0
            self.emitir("MOV", AL, mem(self.direccion_de(token)))
            self.emitir("MOV", AH, imm(0))
            self.avanzar()
        else:
            self.emitir("MOV", AX, self.fuente())

    def es_simple(self) -> bool:  # un solo ID int / NUM, sin operador detrás
        token = self.token_actual()
        return (
            token.kind in (T.ID, T.NUM)
            and self.tabla.get(token.lexeme) != "bool"
            and self.tokens[self.posicion + 1].kind not in ARITMETICOS
        )

    def fuente(self) -> tuple:  # ID -> [dirección] · NUM -> número · true / false -> 1 / 0
        token = self.token_actual()
        self.avanzar()
        if token.kind == T.ID:
            return mem(self.direccion_de(token))
        return imm(int(token.lexeme) if token.kind == T.NUM else int(token.kind == T.TRUE))

    def direccion_de(self, token: Token) -> int:
        if token.lexeme not in self.direcciones:
            raise ErrorObjeto(
                f"Línea {token.line}: ERROR DE CÓDIGO OBJETO: "
                f"La variable '{token.lexeme}' no ha sido declarada."
            )
        return self.direcciones[token.lexeme]

    # ---------- emisión ----------

    def emitir(self, mnemonico: str, *operandos: tuple, forzar: str | None = None, texto: str = "") -> None:
        partes = ", ".join(texto_de(operando) for operando in operandos)
        self.items.append(Instruccion(mnemonico, operandos, forzar, texto or f"{mnemonico} {partes}".strip()))

    def salto(self, mnemonico: str, etiqueta: str) -> None:
        self.items.append(Salto(mnemonico, etiqueta))

    def etiqueta(self, nombre: str) -> None:
        self.items.append(Etiqueta(nombre))

    def nueva_etiqueta(self, prefijo: str) -> str:
        self.numero_etiqueta += 1
        return f"{prefijo}_{self.numero_etiqueta}"


def ensamblar(items: list) -> list[tuple[int, list[int], str]]:
    """Dos pasadas: la 1 calcula direcciones; la 2 ya conoce los destinos de los saltos."""
    destinos: dict[str, int] = {}
    for _ in range(2):
        filas, posicion = [], CODE_BASE
        for item in items:
            if isinstance(item, Etiqueta):
                destinos[item.nombre] = posicion
                continue
            if isinstance(item, Salto):
                codigo = codificar_salto(item.mnemonico, destinos.get(item.etiqueta, 0), posicion)
                texto = f"{item.mnemonico} {item.etiqueta}"
            else:
                codigo, texto = codificar(item.mnemonico, item.operandos, item.forzar), item.texto
            filas.append((posicion, codigo, texto))
            posicion += len(codigo)
    return filas


def formatear_direccion(direccion: int) -> str:
    return " ".join(f"{(direccion >> desplazamiento) & 0xF:04b}" for desplazamiento in (12, 8, 4, 0))


def formatear_binario(codigo: list[int]) -> str:
    return "  ".join(f"{byte >> 4:04b} {byte & 0xF:04b}" for byte in codigo)


def formatear_hex(codigo: list[int]) -> str:
    return " ".join(f"{byte:02X}" for byte in codigo)


def fila(direccion: int, codigo: list[int], texto: str) -> dict[str, str]:
    """Una fila del panel: DIR y CONTENIDO en nibbles (4 bits), HEX en bytes."""
    return {
        "direccion": formatear_direccion(direccion),
        "contenido": formatear_binario(codigo),
        "hex": formatear_hex(codigo),
        "texto": texto,
    }


def generar_codigo_objeto(tokens: list[Token], tabla: dict[str, str]):
    generador = GeneradorObjeto(tokens, tabla)
    try:
        filas = generador.generar()
    except (ErrorObjeto, ErrorCodificador) as error:
        return False, [], [], [str(error)]
    datos = [  # int ocupa 2 bytes; bool, COC y RESI ocupan 1
        fila(
            direccion,
            [0] * (2 if tabla.get(nombre) == "int" else 1),
            f"{nombre} : {tabla.get(nombre, 'byte')}",
        )
        for nombre, direccion in generador.direcciones.items()
    ]
    return True, datos, [fila(*datos_fila) for datos_fila in filas], ["Código Objeto OK"]
