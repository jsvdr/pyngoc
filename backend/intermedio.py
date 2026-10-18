# Intermedio: tabla + tokens -> filas de 3 campos (Nombre, Operador, Atributo).
# La tabla llena el .DATA; los tokens llenan el .CODE.
#
# El generador arma líneas de texto TASM ("MOV AX, a"). Al final, partir_linea()
# corta cada línea en 3 campos: Nombre = etiqueta o variable, Operador =
# instrucción o directiva, Atributo = el resto.
#
# Aritmética simple (T = A OP B) se emite directa: MOV Reg, A / OP Reg, B /
# MOV T, Reg. Si un operando es compuesto, se cae a la versión con pila.
from tokens import Token, TokenKind

# Palabras que van en la columna Operador (nunca son un nombre).
INSTRUCCIONES = frozenset(
    {
        "TITLE",
        ".MODEL",
        ".486",
        ".STACK",
        ".DATA",
        ".CODE",
        ".STARTUP",
        ".EXIT",
        "DW",
        "DB",
        "PROC",
        "ENDP",
        "END",
        "MOV",
        "ADD",
        "SUB",
        "MUL",
        "DIV",
        "CMP",
        "SETE",
        "SETA",
        "SETB",
        "PUSH",
        "POP",
        "INC",
        "LOOP",
        "INT",
        "JMP",
        "JE",
        "JNE",
        "JGE",
        "JLE",
    }
)

# --- Esqueleto del programa ---
CABECERA = ["TITLE Pyngo", ".MODEL Small", ".486", ".STACK", "", ".DATA"]

CODIGO = ["", ".CODE", "MAIN PROC FAR", ".STARTUP", ""]

PIE = ["", ".EXIT", "MAIN ENDP", "", "END"]


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


# Generador: copia la forma del parser, pero en vez de reconocer va
# juntando líneas TASM. El resultado de cada expresión queda en AX: la
# izquierda se apila, la derecha se calcula y se pasan a AX=izquierda y
# BX=derecha.
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

    # DECL → DECL_VAR | ASIGNACION | IF | PRINT
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

        # Simple: un solo literal -> MOV var, literal (una línea).
        if self.es_expr_simple():
            valor = self.valor_factor(self.token_actual())

            self.avanzar()

            self.emitir(f"MOV {nombre_variable}, {valor}")

            return

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

        # Simple: un solo literal -> MOV var, literal (una línea).
        if self.es_expr_simple():
            valor = self.valor_factor(self.token_actual())

            self.avanzar()

            self.emitir(f"MOV {nombre_variable}, {valor}")

            return

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

        if self.es_comparacion_simple():
            if self.token_actual_es(TokenKind.LPAREN):
                self.avanzar()

            izquierda = self.valor_factor(self.token_actual())

            self.avanzar()

            operador = self.token_actual().kind

            self.avanzar()

            derecha = self.valor_factor(self.token_actual())

            self.avanzar()

            if self.token_actual_es(TokenKind.RPAREN):
                self.avanzar()

            self.emitir(f"MOV AX, {izquierda}")
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

    # EXPRESION → SUMA [ ( == | > | < ) SUMA ]
    # Compara sin signo: SETE / SETA / SETB.
    def expresion(self) -> None:
        self.suma()

        if (
            self.token_actual_es(TokenKind.EQ)
            or self.token_actual_es(TokenKind.GREATER)
            or self.token_actual_es(TokenKind.LESS)
        ):
            operador = self.token_actual().kind

            self.avanzar()

            self.apilar_ax()
            self.suma()
            self.recoger_en_bx()

            if operador == TokenKind.EQ:
                mnemonico = "SETE"
            elif operador == TokenKind.GREATER:
                mnemonico = "SETA"
            else:
                mnemonico = "SETB"

            self.emitir("CMP AX, BX")
            self.emitir(f"{mnemonico} AL")
            self.emitir("MOV AH, 0")

    # SUMA → TERMINO [ ( @ | # ) TERMINO ]*
    # Simple directa: MOV Reg, A / OP Reg, B. Si el operando es compuesto,
    # se cae a la versión con pila.
    def suma(self) -> None:
        self.termino()

        while self.token_actual_es(TokenKind.AT) or self.token_actual_es(
            TokenKind.HASH
        ):
            operador = self.token_actual().kind

            self.avanzar()

            if self.es_factor_simple():
                valor = self.valor_factor(self.token_actual())

                self.avanzar()

                if operador == TokenKind.AT:
                    self.emitir(f"ADD AX, {valor}")
                else:
                    self.emitir(f"SUB AX, {valor}")

            else:
                self.apilar_ax()
                self.termino()
                self.recoger_en_bx()

                if operador == TokenKind.AT:
                    self.emitir("ADD AX, BX")
                else:
                    self.emitir("SUB AX, BX")

    # TERMINO → FACTOR [ ( & | | ) FACTOR ]*
    # Simple directa: MUL/DIV con el operando directo. Si es compuesto,
    # se cae a la versión con pila.
    def termino(self) -> None:
        self.factor()

        while self.token_actual_es(TokenKind.AMPERSAND) or self.token_actual_es(
            TokenKind.PIPE
        ):
            operador = self.token_actual().kind

            self.avanzar()

            if self.es_factor_simple():
                if operador == TokenKind.AMPERSAND:
                    if self.token_actual_es(TokenKind.ID):
                        variable = self.token_actual().lexeme

                        self.avanzar()

                        self.emitir(f"MUL {variable}")
                    else:
                        valor = self.valor_factor(self.token_actual())

                        self.avanzar()

                        self.emitir(f"MOV BX, {valor}")
                        self.emitir("MUL BX")

                else:
                    self.emitir("MOV DX, 0")

                    if self.token_actual_es(TokenKind.ID):
                        variable = self.token_actual().lexeme

                        self.avanzar()

                        self.emitir(f"DIV {variable}")
                    else:
                        valor = self.valor_factor(self.token_actual())

                        self.avanzar()

                        self.emitir(f"MOV BX, {valor}")
                        self.emitir("DIV BX")

            else:
                self.apilar_ax()
                self.factor()
                self.recoger_en_bx()

                if operador == TokenKind.AMPERSAND:
                    self.emitir("MUL BX")
                else:
                    self.emitir("MOV DX, 0")
                    self.emitir("DIV BX")

    # FACTOR → ID | NUM | BOOL | ( EXPRESION )
    def factor(self) -> None:
        if self.token_actual_es(TokenKind.ID):
            nombre_variable = self.token_actual().lexeme

            self.avanzar()

            self.emitir(f"MOV AX, {nombre_variable}")
            return

        if self.token_actual_es(TokenKind.NUM):
            numero = self.token_actual().lexeme

            self.avanzar()

            self.emitir(f"MOV AX, {numero}")
            return

        if self.token_actual_es(TokenKind.TRUE) or self.token_actual_es(
            TokenKind.FALSE
        ):
            valor = 1 if self.token_actual_es(TokenKind.TRUE) else 0

            self.avanzar()

            self.emitir(f"MOV AX, {valor}")
            return

        if self.token_actual_es(TokenKind.LPAREN):
            self.avanzar()

            self.expresion()

            self.avanzar_si_es(TokenKind.RPAREN)
            return

    # La izquierda se guarda en la pila mientras se calcula la derecha.
    def apilar_ax(self) -> None:
        self.emitir("PUSH AX")

    # Con la derecha en AX y la izquierda en la pila: AX=izq, BX=der.
    def recoger_en_bx(self) -> None:
        self.emitir("MOV BX, AX")
        self.emitir("POP AX")

    # Una línea TASM más.
    def emitir(self, linea: str) -> None:
        self.lineas.append(linea)

    # Una etiqueta en la columna Nombre.
    def etiqueta(self, nombre: str) -> None:
        self.lineas.append(f"{nombre}:")

    def nueva_etiqueta(self) -> str:
        self.numero_etiqueta += 1
        return f"ETQ{self.numero_etiqueta}"

    # ¿La expresión actual es un solo factor literal o variable?
    def es_expr_simple(self) -> bool:
        if not (
            self.token_actual_es(TokenKind.ID)
            or self.token_actual_es(TokenKind.NUM)
            or self.token_actual_es(TokenKind.TRUE)
            or self.token_actual_es(TokenKind.FALSE)
        ):
            return False

        posicion_siguiente = self.posicion + 1

        if posicion_siguiente < len(self.tokens):
            tipo_siguiente = self.tokens[posicion_siguiente].kind

            if tipo_siguiente in (
                TokenKind.AT,
                TokenKind.HASH,
                TokenKind.AMPERSAND,
                TokenKind.PIPE,
                TokenKind.EQ,
                TokenKind.GREATER,
                TokenKind.LESS,
            ):
                return False

        return True

    # ¿El factor actual es simple (ID/NUM/BOOL) y no va seguido de & o |?
    def es_factor_simple(self) -> bool:
        if not (
            self.token_actual_es(TokenKind.ID)
            or self.token_actual_es(TokenKind.NUM)
            or self.token_actual_es(TokenKind.TRUE)
            or self.token_actual_es(TokenKind.FALSE)
        ):
            return False

        posicion_siguiente = self.posicion + 1

        if posicion_siguiente < len(self.tokens):
            tipo_siguiente = self.tokens[posicion_siguiente].kind

            if tipo_siguiente in (TokenKind.AMPERSAND, TokenKind.PIPE):
                return False

        return True

    # ¿La condición es una comparación simple (factor OP factor)?
    def es_comparacion_simple(self) -> bool:
        posicion = self.posicion

        if posicion >= len(self.tokens):
            return False

        # Se permite un paréntesis inicial.
        if self.tokens[posicion].kind == TokenKind.LPAREN:
            posicion += 1

        if posicion >= len(self.tokens):
            return False

        if self.tokens[posicion].kind not in (
            TokenKind.ID,
            TokenKind.NUM,
            TokenKind.TRUE,
            TokenKind.FALSE,
        ):
            return False

        posicion += 1

        if posicion >= len(self.tokens):
            return False

        if self.tokens[posicion].kind not in (
            TokenKind.EQ,
            TokenKind.GREATER,
            TokenKind.LESS,
        ):
            return False

        posicion += 1

        if posicion >= len(self.tokens):
            return False

        if self.tokens[posicion].kind not in (
            TokenKind.ID,
            TokenKind.NUM,
            TokenKind.TRUE,
            TokenKind.FALSE,
        ):
            return False

        posicion += 1

        if posicion >= len(self.tokens):
            return False

        return self.tokens[posicion].kind in (
            TokenKind.RPAREN,
            TokenKind.LBRACE,
            TokenKind.SEMICOLON,
            TokenKind.EOF,
        )

    # Valor de un factor simple (ID/NUM/TRUE/FALSE) como texto.
    def valor_factor(self, token: Token) -> str:
        if token.kind == TokenKind.TRUE:
            return "1"

        if token.kind == TokenKind.FALSE:
            return "0"

        return token.lexeme

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
