# Intermedio: tabla + tokens -> filas de 3 campos (Nombre, Operador, Atributo).
# Cada expresión se calcula en AX y solo se admiten operandos simples
# (variable, número o true/false). Los bool son DB: se cargan con AL y AH queda en 0.
from recorrido import Recorrido
from tokens import Token
from tokens import TokenKind as T


class ErrorIntermedio(Exception):
    """Construcción que esta versión sencilla del generador no produce."""


CABECERA = [
    ("", "TITLE", "Pyngo"),
    ("", ".MODEL", "Small"),
    ("", ".486", ""),
    ("", ".STACK", ""),
    ("", "", ""),
    ("", ".DATA", ""),
]
CODIGO = [
    ("", "", ""),
    ("", ".CODE", ""),
    ("MAIN", "PROC", "FAR"),
    ("", ".STARTUP", ""),
    ("", "", ""),
]
PIE = [
    ("", "", ""),
    ("", ".EXIT", ""),
    ("MAIN", "ENDP", ""),
    ("", "", ""),
    ("", "END", ""),
]

SALTO_SI_FALSO = {T.LESS: "JAE", T.GREATER: "JBE", T.EQ: "JNE"}  # sin signo, igual que el CO
SET_SI_CIERTO = {T.EQ: "SETE", T.GREATER: "SETA", T.LESS: "SETB"}
PROHIBIDO_TRAS_SUMA = (T.AMPERSAND, T.PIPE)
PROHIBIDO_TRAS_COMPARACION = (T.AT, T.HASH, T.AMPERSAND, T.PIPE)


class Generador(Recorrido):
    def __init__(self, tokens: list[Token], tabla: dict[str, str]) -> None:
        super().__init__(tokens)
        self.filas: list[tuple[str, str, str]] = []
        self.numero_etiqueta = 0
        self.tabla = tabla

    # ---------- sentencias ----------

    def bloque(self) -> None:  # { LISTA_DECL }: sirve para el programa, if y while
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
        nombre = self.token_actual().lexeme
        self.avanzar()  # ID
        self.avanzar()  # =
        self.expresion()
        self.emitir(f"MOV {nombre}, {'AL' if self.tabla.get(nombre) == 'bool' else 'AX'}")

    # Salta a etiqueta_falsa si la condición es falsa. Una comparación simple (a < b)
    # usa CMP + salto directo; cualquier otra expresión se evalúa y se compara con 0.
    def condicion(self, nombre: str, etiqueta_falsa: str) -> None:
        self.avanzar()  # if / while
        self.avanzar_si_es(T.LPAREN)
        if self.es_comparacion():
            self.emitir(f"{SALTO_SI_FALSO[self.comparar()]} {etiqueta_falsa}")
        else:
            self.expresion()
            self.emitir("CMP AX, 0")
            self.emitir(f"JE {etiqueta_falsa}")
        self.avanzar_si_es(T.RPAREN)
        if not self.token_actual_es(T.LBRACE):
            raise ErrorIntermedio(f"En el {nombre}, los paréntesis deben rodear toda la condición.")

    def if_stmt(self) -> None:
        falso = self.nueva_etiqueta("IF_FALSO")
        self.condicion("if", falso)
        self.bloque()
        self.etiqueta(falso)

    def while_stmt(self) -> None:
        inicio, fin = self.nueva_etiqueta("WHILE_INICIO"), self.nueva_etiqueta("WHILE_FIN")
        self.etiqueta(inicio)
        self.condicion("while", fin)
        self.bloque()
        self.emitir(f"JMP {inicio}")
        self.etiqueta(fin)

    # Carga la variable en AX, divide entre 10 para sacar cifras y las imprime con INT 21H.
    def print_stmt(self) -> None:
        self.avanzar()  # print
        self.avanzar()  # (
        nombre = self.token_actual().lexeme
        self.avanzar()  # ID
        self.avanzar()  # )
        self.emitir(f"MOV AX, {nombre}")
        self.emitir("MOV DL, 10")
        self.emitir("DIV DL")
        self.emitir("MOV COC, AL")
        self.emitir("MOV RESI, AH")
        for digito in ("COC", "RESI"):
            self.emitir(f"MOV DL, {digito}")
            self.emitir("ADD DL, 30H")
            self.emitir("MOV AH, 02H")
            self.emitir("INT 21H")

    # ---------- expresiones ----------

    def expresion(self) -> None:  # COMPARACION | SUMA
        if self.es_comparacion():
            self.emitir(f"{SET_SI_CIERTO[self.comparar()]} AL")
            self.emitir("MOV AH, 0")
            return
        self.suma()
        if self.token_actual().kind in SET_SI_CIERTO:
            raise ErrorIntermedio("En una comparación, los dos lados deben ser operandos simples.")

    def comparar(self) -> T:  # a (== | > | <) b: deja los flags listos y devuelve el operador
        self.cargar_en_ax(self.operando())
        operador = self.token_actual().kind
        self.avanzar()
        derecha = self.operando()
        self.exigir_simple("la comparación", PROHIBIDO_TRAS_COMPARACION)
        es_bool = self.tabla.get(derecha) == "bool" or derecha in ("true", "false")
        derecha_txt = "1" if derecha == "true" else ("0" if derecha == "false" else derecha)
        self.emitir(f"CMP {'AL' if es_bool else 'AX'}, {derecha_txt}")
        return operador

    def suma(self) -> None:  # TERMINO [ ( @ | # ) OPERANDO ]*
        self.termino()
        while self.token_actual().kind in (T.AT, T.HASH):
            mnemonico = "ADD" if self.token_actual_es(T.AT) else "SUB"
            self.avanzar()
            derecha = self.operando()
            self.exigir_simple("la suma o la resta", PROHIBIDO_TRAS_SUMA)
            self.emitir(f"{mnemonico} AX, {derecha}")

    def termino(self) -> None:  # OPERANDO [ ( & | | ) OPERANDO ]*
        self.cargar_en_ax(self.operando())
        while self.token_actual().kind in (T.AMPERSAND, T.PIPE):
            mnemonico = self.token_actual().kind
            self.avanzar()
            self.emitir(f"MOV BX, {self.operando()}")
            if mnemonico == T.AMPERSAND:
                self.emitir("MUL BX")
            else:
                self.emitir("MOV DX, 0")
                self.emitir("DIV BX")

    def operando(self) -> str:  # ID | NUM | true | false, como texto
        token = self.token_actual()
        if token.kind in (T.TRUE, T.FALSE):
            self.avanzar()
            return token.lexeme
        if token.kind in (T.ID, T.NUM):
            self.avanzar()
            return token.lexeme
        if token.kind == T.LPAREN:
            raise ErrorIntermedio("No se admiten paréntesis dentro de una expresión.")
        raise ErrorIntermedio("Se esperaba una variable, un número o true/false.")

    def cargar_en_ax(self, operando: str) -> None:  # un bool es DB: se carga en AL y AH queda en 0
        if self.tabla.get(operando) == "bool" or operando in ("true", "false"):
            valor = "1" if operando == "true" else ("0" if operando == "false" else operando)
            self.emitir(f"MOV AL, {valor}")
            self.emitir("MOV AH, 0")
        else:
            self.emitir(f"MOV AX, {operando}")

    def exigir_simple(self, contexto: str, prohibidos: tuple[T, ...]) -> None:
        if self.token_actual().kind in prohibidos:
            raise ErrorIntermedio(f"El lado derecho de {contexto} debe ser un operando simple.")

    def es_comparacion(self) -> bool:  # ¿"operando ( == | > | < ) ..."?
        return self.posicion + 1 < len(self.tokens) and self.tokens[self.posicion + 1].kind in SET_SI_CIERTO

    # ---------- emisión ----------

    def emitir(self, linea: str) -> None:  # "MOV AX, a" -> ("", "MOV", "AX, a")
        operador, _, atributo = linea.partition(" ")
        self.filas.append(("", operador, atributo))

    def etiqueta(self, nombre: str) -> None:
        self.filas.append((f"{nombre}:", "", ""))

    def nueva_etiqueta(self, prefijo: str) -> str:
        self.numero_etiqueta += 1
        return f"{prefijo}_{self.numero_etiqueta}"


def generar_codigo_intermedio(tabla: dict[str, str], tokens: list[Token]) -> list[tuple[str, str, str]]:
    tiene_print = any(token.kind == T.PRINT for token in tokens)
    if not tabla and not tiene_print:
        return []
    filas = list(CABECERA)
    for nombre, tipo in tabla.items():
        filas.append((nombre, "DW" if tipo == "int" else "DB", "?"))
    if tiene_print:  # donde el print parte el número en decenas y unidades
        filas += [("COC", "DB", "?"), ("RESI", "DB", "?")]
    generador = Generador(tokens, tabla)
    generador.bloque()
    return filas + CODIGO + generador.filas + PIE
