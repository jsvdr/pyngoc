# Intermedio: tabla + tokens -> filas de 3 campos (Nombre, Operador, Atributo).
# La tabla llena el .DATA; los tokens llenan el .CODE.
#
# El generador arma líneas de texto TASM ("MOV AX, a"). Al final, partir_linea()
# corta cada línea en 3 campos: Nombre = etiqueta o variable, Operador =
# instrucción o directiva, Atributo = el resto.
#
# Versión sencilla: cada expresión se calcula en AX y solo se admiten operandos
# simples (variable, número o true/false). Se pueden encadenar operaciones del
# mismo nivel (@ # o & |). Si una expresión necesitara la pila, se lanza
# ErrorIntermedio.
#
# Los bool son DB (1 byte): se cargan con MOV AL y se limpia AH, y al comparar
# dos bool se usa CMP AL. Así AX siempre queda con el valor completo.
from tokens import Token, TokenKind


class ErrorIntermedio(Exception):
    """Construcción que esta versión sencilla del generador no produce."""


# Palabras que van en la columna Operador (nunca son un nombre).
INSTRUCCIONES = frozenset(
    "TITLE .MODEL .486 .STACK .DATA .CODE .STARTUP .EXIT "
    "DW DB PROC ENDP END "
    "MOV ADD SUB MUL DIV CMP SETE SETA SETB "
    "INT "
    "JMP JE JNE JGE JLE".split()
)

# --- Esqueleto del programa ---
CABECERA = ["TITLE Pyngo", ".MODEL Small", ".486", ".STACK", "", ".DATA"]

CODIGO = ["", ".CODE", "MAIN PROC FAR", ".STARTUP", ""]

PIE = ["", ".EXIT", "MAIN ENDP", "", "END"]


# Operadores de multiplicación/división: no pueden ir tras el lado derecho
# de una suma o una resta (sería un término compuesto).
PROHIBIDO_TRAS_SUMA = (TokenKind.AMPERSAND, TokenKind.PIPE)

# Tras el lado derecho de una comparación no puede venir ninguna operación.
PROHIBIDO_TRAS_COMPARACION = (
    TokenKind.AT,
    TokenKind.HASH,
    TokenKind.AMPERSAND,
    TokenKind.PIPE,
)


# Corta una línea TASM en (Nombre, Operador, Atributo).
def partir_linea(linea: str) -> tuple[str, str, str]:
    linea = linea.strip()

    if linea == "":
        return ("", "", "")

    if linea.endswith(":"):
        return (linea, "", "")

    partes = linea.split(" ", 1)

    if partes[0] in INSTRUCCIONES:
        return ("", partes[0], partes[1] if len(partes) > 1 else "")

    resto = partes[1].split(" ", 1) if len(partes) > 1 else [""]

    return (partes[0], resto[0], resto[1] if len(resto) > 1 else "")


# Generador: copia la forma del parser, pero en vez de reconocer va juntando
# líneas TASM. El resultado de cada expresión queda en AX.
class Generador:
    tokens: list[Token]
    posicion: int
    lineas: list[str]
    numero_etiqueta: int
    # nombre_variable -> "int" o "bool" (los bool son DB: van con AL/AH)
    tabla: dict[str, str]

    def __init__(self, tokens: list[Token], tabla: dict[str, str]) -> None:
        self.tokens = tokens
        self.posicion = 0
        self.lineas = []
        self.numero_etiqueta = 0
        self.tabla = tabla

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
    # La variable ya está en el .DATA: aquí solo se guarda su valor.
    def decl_var(self) -> None:
        tipo_declarado = self.tipo_dato()

        nombre_variable = self.token_actual().lexeme

        self.avanzar_si_es(TokenKind.ID)
        self.avanzar_si_es(TokenKind.ASSIGN)

        self.expresion()

        if tipo_declarado == "bool":
            self.emitir(f"MOV {nombre_variable}, AL")
        else:
            self.emitir(f"MOV {nombre_variable}, AX")

    # ASIGNACION → ID = EXPRESION
    def asignacion(self) -> None:
        nombre_variable = self.token_actual().lexeme

        self.avanzar_si_es(TokenKind.ID)
        self.avanzar_si_es(TokenKind.ASSIGN)

        self.expresion()

        if self.tabla.get(nombre_variable) == "bool":
            self.emitir(f"MOV {nombre_variable}, AL")
        else:
            self.emitir(f"MOV {nombre_variable}, AX")

    # Deja la condición evaluada en AX/flags y SALTA si resulta falsa.
    # Si es una comparación simple (a < b) se emite CMP + salto directo, como en
    # la plantilla del profe; si no, se evalúa a AX y se salta si queda en cero.
    # El if salta a su etiqueta else y el while a la etiqueta de fin.
    def condicion_falsa(self, etiqueta_falsa: str) -> None:
        if self.es_comparacion():
            izquierda = self.operando()

            self.cargar_en_ax(izquierda)

            operador = self.token_actual().kind

            self.avanzar()

            derecha = self.operando()

            self.exigir_simple("la comparación", PROHIBIDO_TRAS_COMPARACION)

            self.comparar_con(derecha)

            if operador == TokenKind.LESS:
                self.emitir(f"JGE {etiqueta_falsa}")
            elif operador == TokenKind.GREATER:
                self.emitir(f"JLE {etiqueta_falsa}")
            else:
                self.emitir(f"JNE {etiqueta_falsa}")

        else:
            self.expresion()

            self.emitir("CMP AX, 0")
            self.emitir(f"JE {etiqueta_falsa}")

    # IF → if EXPRESION { LISTA_DECL } [ else { LISTA_DECL } ]
    def if_stmt(self) -> None:
        etiqueta_else = self.nueva_etiqueta("IF_FALSO")

        self.avanzar_si_es(TokenKind.IF)
        self.avanzar_si_es(TokenKind.LPAREN)

        self.condicion_falsa(etiqueta_else)

        self.avanzar_si_es(TokenKind.RPAREN)
        self.avanzar_si_es(TokenKind.LBRACE)

        self.lista_decl()

        self.avanzar_si_es(TokenKind.RBRACE)

        if self.token_actual_es(TokenKind.ELSE):
            etiqueta_fin = self.nueva_etiqueta("IF_FIN")

            self.avanzar()

            self.emitir(f"JMP {etiqueta_fin}")
            self.etiqueta(etiqueta_else)

            self.avanzar_si_es(TokenKind.LBRACE)

            self.lista_decl()

            self.avanzar_si_es(TokenKind.RBRACE)

            self.etiqueta(etiqueta_fin)

        else:
            self.etiqueta(etiqueta_else)

    # WHILE → while EXPRESION { LISTA_DECL }
    # Prueba la condición antes de cada vuelta: si sigue siendo cierta, repite.
    def while_stmt(self) -> None:
        etiqueta_inicio = self.nueva_etiqueta("WHILE_INICIO")
        etiqueta_fin = self.nueva_etiqueta("WHILE_FIN")

        self.etiqueta(etiqueta_inicio)

        self.avanzar_si_es(TokenKind.WHILE)
        self.avanzar_si_es(TokenKind.LPAREN)

        self.condicion_falsa(etiqueta_fin)

        self.avanzar_si_es(TokenKind.RPAREN)
        self.avanzar_si_es(TokenKind.LBRACE)

        self.lista_decl()

        self.avanzar_si_es(TokenKind.RBRACE)

        # Vuelve al inicio para volver a probar la condición.
        self.emitir(f"JMP {etiqueta_inicio}")
        self.etiqueta(etiqueta_fin)

    # PRINT → print ( EXPRESION )
    # El valor queda en AX y se parte en 2 dígitos: COC = decenas y RESI =
    # unidades. Cada uno se pasa a ASCII sumando 30H y se imprime con
    # INT 21H / AH=02H, igual que en la plantilla del profe.
    def print_stmt(self) -> None:
        self.avanzar_si_es(TokenKind.PRINT)
        self.avanzar_si_es(TokenKind.LPAREN)

        self.expresion()

        self.avanzar_si_es(TokenKind.RPAREN)

        # AX / 10 -> AL = decenas, AH = unidades.
        self.emitir("MOV DL, 10")
        self.emitir("DIV DL")
        self.emitir("MOV COC, AL")
        self.emitir("MOV RESI, AH")

        # Primero las decenas y después las unidades.
        self.emitir("MOV DL, COC")
        self.emitir("ADD DL, 30H")
        self.emitir("MOV AH, 02H")
        self.emitir("INT 21H")

        self.emitir("MOV DL, RESI")
        self.emitir("ADD DL, 30H")
        self.emitir("MOV AH, 02H")
        self.emitir("INT 21H")

    # TIPO_DATO → int | bool
    def tipo_dato(self) -> str | None:
        if self.token_actual_es(TokenKind.INT):
            self.avanzar()
            return "int"

        if self.token_actual_es(TokenKind.BOOL):
            self.avanzar()
            return "bool"

        return None

    # EXPRESION → COMPARACION | SUMA
    # La comparación es directa (CMP + SETcc) y deja 0 o 1 en AX.
    def expresion(self) -> None:
        if self.es_comparacion():
            izquierda = self.operando()

            self.cargar_en_ax(izquierda)

            operador = self.token_actual().kind

            self.avanzar()

            derecha = self.operando()

            self.exigir_simple("la comparación", PROHIBIDO_TRAS_COMPARACION)

            self.comparar_con(derecha)

            if operador == TokenKind.EQ:
                self.emitir("SETE AL")
            elif operador == TokenKind.GREATER:
                self.emitir("SETA AL")
            else:
                self.emitir("SETB AL")

            self.emitir("MOV AH, 0")
            return

        self.suma()

        if (
            self.token_actual_es(TokenKind.EQ)
            or self.token_actual_es(TokenKind.GREATER)
            or self.token_actual_es(TokenKind.LESS)
        ):
            raise ErrorIntermedio(
                "En una comparación, los dos lados deben ser operandos simples."
            )

    # SUMA → TERMINO [ ( @ | # ) OPERANDO ]*   (@ suma, # resta)
    def suma(self) -> None:
        self.termino()

        while self.token_actual_es(TokenKind.AT) or self.token_actual_es(
            TokenKind.HASH
        ):
            operador = self.token_actual().kind

            self.avanzar()

            derecha = self.operando()

            self.exigir_simple("la suma o la resta", PROHIBIDO_TRAS_SUMA)

            if operador == TokenKind.AT:
                self.emitir(f"ADD AX, {derecha}")
            else:
                self.emitir(f"SUB AX, {derecha}")

    # TERMINO → OPERANDO [ ( & | | ) OPERANDO ]*   (& multiplica, | divide)
    def termino(self) -> None:
        izquierda = self.operando()

        self.cargar_en_ax(izquierda)

        while self.token_actual_es(TokenKind.AMPERSAND) or self.token_actual_es(
            TokenKind.PIPE
        ):
            operador = self.token_actual().kind

            self.avanzar()

            derecha = self.operando()

            self.emitir(f"MOV BX, {derecha}")

            if operador == TokenKind.AMPERSAND:
                self.emitir("MUL BX")
            else:
                self.emitir("MOV DX, 0")
                self.emitir("DIV BX")

    # OPERANDO → ID | NUM | true | false   (devuelve el valor como texto)
    def operando(self) -> str:
        token = self.token_actual()

        if token.kind == TokenKind.TRUE:
            self.avanzar()
            return "1"

        if token.kind == TokenKind.FALSE:
            self.avanzar()
            return "0"

        if token.kind in (TokenKind.ID, TokenKind.NUM):
            self.avanzar()
            return token.lexeme

        if token.kind == TokenKind.LPAREN:
            raise ErrorIntermedio("No se admiten paréntesis dentro de una expresión.")

        raise ErrorIntermedio("Se esperaba una variable, un número o true/false.")

    # Carga un operando en AX. Si es una variable bool la carga con AL y limpia
    # AH, porque los bool son DB (1 byte) y no entran en un MOV de 16 bits. Así
    # AX queda valiendo 0 o 1 y el resto del código sigue igual.
    def cargar_en_ax(self, operando: str) -> None:
        if self.tabla.get(operando) == "bool":
            self.emitir(f"MOV AL, {operando}")
            self.emitir("MOV AH, 0")
        else:
            self.emitir(f"MOV AX, {operando}")

    # Compara AX con otro operando. Si el otro es un bool (DB) compara con AL:
    # no se puede mezclar un registro de 16 bits con un byte. Eso solo pasa en
    # "bool == bool", porque el semántico exige el mismo tipo en la comparación.
    def comparar_con(self, operando: str) -> None:
        if self.tabla.get(operando) == "bool":
            self.emitir(f"CMP AL, {operando}")
        else:
            self.emitir(f"CMP AX, {operando}")

    # El lado derecho no puede traer una operación de otro nivel: si fuera
    # compuesto haría falta la pila, que esta versión no usa.
    def exigir_simple(self, contexto: str, prohibidos: tuple[TokenKind, ...]) -> None:
        if self.token_actual().kind in prohibidos:
            raise ErrorIntermedio(
                f"El lado derecho de {contexto} debe ser un operando simple."
            )

    # ¿La expresión actual es "operando ( == | > | < ) ..."?
    def es_comparacion(self) -> bool:
        posicion_siguiente = self.posicion + 1

        if posicion_siguiente >= len(self.tokens):
            return False

        return self.tokens[posicion_siguiente].kind in (
            TokenKind.EQ,
            TokenKind.GREATER,
            TokenKind.LESS,
        )

    # Una línea TASM más.
    def emitir(self, linea: str) -> None:
        self.lineas.append(linea)

    # Una etiqueta en la columna Nombre.
    def etiqueta(self, nombre: str) -> None:
        self.lineas.append(f"{nombre}:")

    # Una etiqueta con nombre legible: IF_FIN_2, WHILE_INICIO_1, ...
    def nueva_etiqueta(self, prefijo: str) -> str:
        self.numero_etiqueta += 1
        return f"{prefijo}_{self.numero_etiqueta}"

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


def generar_codigo_intermedio(
    tabla: dict[str, str], tokens: list[Token]
) -> list[tuple[str, str, str]]:
    tiene_print = any(token.kind == TokenKind.PRINT for token in tokens)

    if len(tabla) == 0 and not tiene_print:
        return []

    lineas: list[str] = list(CABECERA)

    for nombre_variable, tipo_declarado in tabla.items():
        if tipo_declarado == "int":
            lineas.append(f"{nombre_variable} DW ?")

        elif tipo_declarado == "bool":
            lineas.append(f"{nombre_variable} DB ?")

    # COC y RESI son la basura donde el print parte el número: solo se declaran
    # si el programa tiene un print.
    if tiene_print:
        lineas.append("COC DB ?")
        lineas.append("RESI DB ?")

    lineas.extend(CODIGO)

    generador = Generador(tokens, tabla)
    generador.programa()

    lineas.extend(generador.lineas)
    lineas.extend(PIE)

    return [partir_linea(linea) for linea in lineas]
