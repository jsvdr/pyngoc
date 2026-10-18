from tokens import Token, TokenKind


# Semántico: lista_tokens -> Semantic OK o errores. Devuelve int/bool/None.
# None = ya hubo error antes, no se genera otro en cascada.
class AnalizadorSemantico:
    tokens: list[Token]
    posicion: int
    errores: list[str]
    # nombre_variable -> "int" o "bool"
    tabla: dict[str, str]

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.posicion = 0
        self.errores = []
        self.tabla = {}

    def analizar(self) -> tuple[bool, list[str]]:
        self.programa()

        if len(self.errores) == 0:
            return True, ["Semantic OK"]

        return False, self.errores

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
    def decl_var(self) -> None:
        # Se guarda ANTES de leer lo demás o apuntaría al ";".
        numero_linea = self.token_actual().line

        tipo_declarado = self.tipo_dato()

        # Si no hay tipo, no se puede guardar. No debería pasar:
        # decl_var solo se llama con int/bool delante.
        if tipo_declarado is None:
            return

        nombre_variable = self.token_actual().lexeme

        self.avanzar_si_es(TokenKind.ID)
        self.avanzar_si_es(TokenKind.ASSIGN)

        tipo_encontrado = self.expresion()

        # ¿La variable ya existe?
        if nombre_variable in self.tabla:
            self.error_declaracion(
                numero_linea, f"La variable '{nombre_variable}' ya fue declarada."
            )
            return

        # ¿Los tipos coinciden?
        if tipo_encontrado is not None and tipo_declarado != tipo_encontrado:
            self.error_tipo(
                numero_linea,
                f"La variable '{nombre_variable}' "
                f"es {tipo_declarado}, "
                f"pero se recibió {tipo_encontrado}.",
            )

        # Se guarda incluso si hubo error de tipos.
        self.tabla[nombre_variable] = tipo_declarado

    # ASIGNACION → ID = EXPRESION
    def asignacion(self) -> None:
        # Se guarda ANTES de leer lo demás o apuntaría al ";".
        numero_linea = self.token_actual().line

        nombre_variable = self.token_actual().lexeme

        self.avanzar_si_es(TokenKind.ID)
        self.avanzar_si_es(TokenKind.ASSIGN)

        tipo_encontrado = self.expresion()

        # ¿La variable existe?
        if nombre_variable not in self.tabla:
            self.error_declaracion(
                numero_linea, f"La variable '{nombre_variable}' no ha sido declarada."
            )

            return

        tipo_declarado = self.tabla[nombre_variable]

        # ¿Los tipos coinciden?
        if tipo_encontrado is not None and tipo_declarado != tipo_encontrado:
            self.error_tipo(
                numero_linea,
                f"La variable '{nombre_variable}' "
                f"es {tipo_declarado}, "
                f"pero se asignó {tipo_encontrado}.",
            )

    # IF → if EXPRESION { LISTA_DECL } [else { LISTA_DECL }]
    def if_stmt(self) -> None:
        numero_linea = self.token_actual().line

        self.avanzar_si_es(TokenKind.IF)

        tipo_de_la_condicion = self.expresion()

        if tipo_de_la_condicion is not None and tipo_de_la_condicion != "bool":
            self.error_tipo(numero_linea, "La condición del if debe ser bool.")

        self.avanzar_si_es(TokenKind.LBRACE)

        self.lista_decl()

        self.avanzar_si_es(TokenKind.RBRACE)

        if self.token_actual_es(TokenKind.ELSE):
            self.avanzar()

            self.avanzar_si_es(TokenKind.LBRACE)

            self.lista_decl()

            self.avanzar_si_es(TokenKind.RBRACE)

    # FOR → for EXPRESION { LISTA_DECL }
    def for_stmt(self) -> None:
        numero_linea = self.token_actual().line

        self.avanzar_si_es(TokenKind.FOR)

        tipo_de_la_condicion = self.expresion()

        if tipo_de_la_condicion is not None and tipo_de_la_condicion != "bool":
            self.error_tipo(numero_linea, "La condición del for debe ser bool.")

        self.avanzar_si_es(TokenKind.LBRACE)

        self.lista_decl()

        self.avanzar_si_es(TokenKind.RBRACE)

    # PRINT → print ( EXPRESION )
    def print_stmt(self) -> None:
        self.avanzar_si_es(TokenKind.PRINT)

        self.avanzar_si_es(TokenKind.LPAREN)

        self.expresion()

        self.avanzar_si_es(TokenKind.RPAREN)

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
    def expresion(self) -> str | None:
        tipo_primero = self.suma()

        # ==
        if self.token_actual_es(TokenKind.EQ):
            numero_linea = self.token_actual().line

            self.avanzar()

            tipo_segundo = self.suma()

            if tipo_primero is None or tipo_segundo is None:
                return None

            if tipo_primero != tipo_segundo:
                self.error_tipo(
                    numero_linea, "Los dos lados de '==' deben tener el mismo tipo."
                )

                return None

            return "bool"

        # > o <
        if self.token_actual_es(TokenKind.GREATER) or self.token_actual_es(
            TokenKind.LESS
        ):
            operador = self.token_actual().lexeme
            numero_linea = self.token_actual().line

            self.avanzar()

            tipo_segundo = self.suma()

            if tipo_primero is None or tipo_segundo is None:
                return None

            if tipo_primero != "int" or tipo_segundo != "int":
                self.error_tipo(
                    numero_linea, f"El operador '{operador}' requiere valores int."
                )

                return None

            return "bool"

        return tipo_primero

    # SUMA → TERMINO [ ( @ | # ) TERMINO ]*
    # Se junta al vuelo, sin árbol: llevo uno, llega otro.
    def suma(self) -> str | None:
        tipo_acumulado = self.termino()

        while self.token_actual_es(TokenKind.AT) or self.token_actual_es(
            TokenKind.HASH
        ):
            operador = self.token_actual().lexeme
            numero_linea = self.token_actual().line

            self.avanzar()

            tipo_nuevo = self.termino()

            if tipo_acumulado is None or tipo_nuevo is None:
                tipo_acumulado = None
                continue

            if tipo_acumulado != "int" or tipo_nuevo != "int":
                self.error_tipo(
                    numero_linea, f"El operador '{operador}' requiere valores int."
                )

                tipo_acumulado = None

            else:
                tipo_acumulado = "int"

        return tipo_acumulado

    # TERMINO → FACTOR [ ( & | | ) FACTOR ]*
    # Se junta al vuelo, sin árbol: llevo uno, llega otro.
    def termino(self) -> str | None:
        tipo_acumulado = self.factor()

        while self.token_actual_es(TokenKind.AMPERSAND) or self.token_actual_es(
            TokenKind.PIPE
        ):
            operador = self.token_actual().lexeme
            numero_linea = self.token_actual().line

            self.avanzar()

            tipo_nuevo = self.factor()

            if tipo_acumulado is None or tipo_nuevo is None:
                tipo_acumulado = None
                continue

            if tipo_acumulado != "int" or tipo_nuevo != "int":
                self.error_tipo(
                    numero_linea, f"El operador '{operador}' requiere valores int."
                )

                tipo_acumulado = None

            else:
                tipo_acumulado = "int"

        return tipo_acumulado

    # FACTOR → ID | NUM | BOOL | ( EXPRESION )
    def factor(self) -> str | None:
        # ID
        if self.token_actual_es(TokenKind.ID):
            nombre_variable = self.token_actual().lexeme
            numero_linea = self.token_actual().line

            self.avanzar()

            if nombre_variable not in self.tabla:
                self.error_declaracion(
                    numero_linea,
                    f"La variable '{nombre_variable}' no ha sido declarada.",
                )

                return None

            return self.tabla[nombre_variable]

        # NUM
        if self.token_actual_es(TokenKind.NUM):
            self.avanzar()

            return "int"

        # true / false
        if self.token_actual_es(TokenKind.TRUE) or self.token_actual_es(
            TokenKind.FALSE
        ):
            self.avanzar()

            return "bool"

        # ( EXPRESION ): lo de dentro manda, vale lo de dentro.
        if self.token_actual_es(TokenKind.LPAREN):
            self.avanzar()

            tipo_dentro_parentesis = self.expresion()

            self.avanzar_si_es(TokenKind.RPAREN)

            return tipo_dentro_parentesis

        return None

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

    def error_tipo(self, numero_linea: int, texto_error: str) -> None:
        self.errores.append(f"Línea {numero_linea}: ERROR DE TIPOS: {texto_error}")

    def error_declaracion(self, numero_linea: int, texto_error: str) -> None:
        self.errores.append(
            f"Línea {numero_linea}: ERROR DE DECLARACIÓN: {texto_error}"
        )
