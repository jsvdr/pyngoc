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
from tokens import Token, TokenKind


class ErrorIntermedio(Exception):
    """Construcción que esta versión sencilla del generador no produce."""


# Palabras que van en la columna Operador (nunca son un nombre).
INSTRUCCIONES = frozenset(
    "TITLE .MODEL .486 .STACK .DATA .CODE .STARTUP .EXIT "
    "DW DB PROC ENDP END "
    "MOV ADD SUB MUL DIV CMP SETE SETA SETB "
    "PUSH POP INC LOOP INT "
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
    # nombre_variable -> "int" o "bool", para saber si guardar AX o AL
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

    # DECL → DECL_VAR | ASIGNACION | IF | FOR | PRINT
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

        if self.token_actual_es(TokenKind.FOR):
            self.for_stmt()
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

    # IF → if EXPRESION { LISTA_DECL } [ else { LISTA_DECL } ]
    # Si la condición es una comparación simple (a < b), se emite CMP + salto
    # directo, como en la plantilla del profe. Si no, se evalúa a AX y se salta
    # si es cero.
    def if_stmt(self) -> None:
        etiqueta_else = self.nueva_etiqueta()

        self.avanzar_si_es(TokenKind.IF)
        self.avanzar_si_es(TokenKind.LPAREN)

        if self.es_comparacion():
            izquierda = self.operando()

            self.emitir(f"MOV AX, {izquierda}")

            operador = self.token_actual().kind

            self.avanzar()

            derecha = self.operando()

            self.exigir_simple("la comparación", PROHIBIDO_TRAS_COMPARACION)

            self.emitir(f"CMP AX, {derecha}")

            if operador == TokenKind.LESS:
                self.emitir(f"JGE {etiqueta_else}")
            elif operador == TokenKind.GREATER:
                self.emitir(f"JLE {etiqueta_else}")
            else:
                self.emitir(f"JNE {etiqueta_else}")

        else:
            self.expresion()

            self.emitir("CMP AX, 0")
            self.emitir(f"JE {etiqueta_else}")

        self.avanzar_si_es(TokenKind.RPAREN)
        self.avanzar_si_es(TokenKind.LBRACE)

        self.lista_decl()

        self.avanzar_si_es(TokenKind.RBRACE)

        if self.token_actual_es(TokenKind.ELSE):
            etiqueta_fin = self.nueva_etiqueta()

            self.avanzar()

            self.emitir(f"JMP {etiqueta_fin}")
            self.etiqueta(etiqueta_else)

            self.avanzar_si_es(TokenKind.LBRACE)

            self.lista_decl()

            self.avanzar_si_es(TokenKind.RBRACE)

            self.etiqueta(etiqueta_fin)

        else:
            self.etiqueta(etiqueta_else)

    # FOR → for EXPRESION { LISTA_DECL }
    # La gramática no trae inicio ni paso, así que es un while.
    def for_stmt(self) -> None:
        etiqueta_inicio = self.nueva_etiqueta()
        etiqueta_fin = self.nueva_etiqueta()

        self.etiqueta(etiqueta_inicio)

        self.avanzar_si_es(TokenKind.FOR)
        self.avanzar_si_es(TokenKind.LPAREN)

        if self.es_comparacion():
            izquierda = self.operando()

            self.emitir(f"MOV AX, {izquierda}")

            operador = self.token_actual().kind

            self.avanzar()

            derecha = self.operando()

            self.exigir_simple("la comparación", PROHIBIDO_TRAS_COMPARACION)

            self.emitir(f"CMP AX, {derecha}")

            if operador == TokenKind.LESS:
                self.emitir(f"JGE {etiqueta_fin}")
            elif operador == TokenKind.GREATER:
                self.emitir(f"JLE {etiqueta_fin}")
            else:
                self.emitir(f"JNE {etiqueta_fin}")

        else:
            self.expresion()

            self.emitir("CMP AX, 0")
            self.emitir(f"JE {etiqueta_fin}")

        self.avanzar_si_es(TokenKind.RPAREN)
        self.avanzar_si_es(TokenKind.LBRACE)

        self.lista_decl()

        self.avanzar_si_es(TokenKind.RBRACE)

        # Vuelve al inicio para volver a probar la condición.
        self.emitir(f"JMP {etiqueta_inicio}")
        self.etiqueta(etiqueta_fin)

    # PRINT → print ( EXPRESION )
    # Imprime cualquier entero no negativo 0..65535 con INT 21H / AH=02H.
    # Extrae los dígitos con divisiones entre 10 (en orden inverso, guardándolos
    # en la pila) y los imprime en orden correcto, convirtiendo cada uno a ASCII
    # sumando 48. El caso 0 se trata aparte.
    def print_stmt(self) -> None:
        self.avanzar_si_es(TokenKind.PRINT)
        self.avanzar_si_es(TokenKind.LPAREN)

        self.expresion()

        self.avanzar_si_es(TokenKind.RPAREN)

        etiqueta_div = self.nueva_etiqueta()
        etiqueta_imp = self.nueva_etiqueta()
        etiqueta_fin = self.nueva_etiqueta()

        # Si el valor es 0, imprimir '0' y terminar.
        self.emitir("CMP AX, 0")
        self.emitir(f"JNE {etiqueta_div}")

        self.emitir("MOV DL, 48")
        self.emitir("MOV AH, 02H")
        self.emitir("INT 21H")
        self.emitir(f"JMP {etiqueta_fin}")

        # Extraer dígitos en orden inverso con divisiones entre 10.
        self.etiqueta(etiqueta_div)
        self.emitir("MOV CX, 0")
        self.emitir("MOV BX, 10")

        self.emitir("MOV DX, 0")
        self.emitir("DIV BX")
        self.emitir("PUSH DX")
        self.emitir("INC CX")
        self.emitir("CMP AX, 0")
        self.emitir(f"JNE {etiqueta_div}")

        # Imprimir dígitos en orden correcto.
        self.etiqueta(etiqueta_imp)
        self.emitir("POP DX")
        self.emitir("ADD DL, 48")
        self.emitir("MOV AH, 02H")
        self.emitir("INT 21H")
        self.emitir(f"LOOP {etiqueta_imp}")

        self.etiqueta(etiqueta_fin)

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

            self.emitir(f"MOV AX, {izquierda}")

            operador = self.token_actual().kind

            self.avanzar()

            derecha = self.operando()

            self.exigir_simple("la comparación", PROHIBIDO_TRAS_COMPARACION)

            self.emitir(f"CMP AX, {derecha}")

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

        self.emitir(f"MOV AX, {izquierda}")

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

    def nueva_etiqueta(self) -> str:
        self.numero_etiqueta += 1
        return f"ETQ{self.numero_etiqueta}"

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

    lineas.extend(CODIGO)

    generador = Generador(tokens, tabla)
    generador.programa()

    lineas.extend(generador.lineas)
    lineas.extend(PIE)

    return [partir_linea(linea) for linea in lineas]
