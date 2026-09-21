from tokens import TokenKind


class AnalizadorSemantico:
    def __init__(self, tokens):
        self.tokens = tokens
        self.indice = 0
        self.errores = []
        self.tabla = {}

    def analizar(self):
        self.programa()

        if len(self.errores) == 0:
            return True, ["Semantic OK"]

        return False, self.errores

    # PROGRAMA → { LISTA_DECL }
    def programa(self):
        self.siguiente_si(TokenKind.LBRACE)

        self.lista_decl()

        self.siguiente_si(TokenKind.RBRACE)

    # LISTA_DECL → [ DECL ; ]*
    def lista_decl(self):
        while not self.es(TokenKind.RBRACE) and not self.es(TokenKind.EOF):
            self.decl()

            self.siguiente_si(TokenKind.SEMICOLON)

    # DECL → DECL_VAR | ASIGNACION | IF | FOR | PRINT
    def decl(self):
        if self.es(TokenKind.INT) or self.es(TokenKind.BOOL):
            self.decl_var()
            return

        if self.es(TokenKind.ID):
            self.asignacion()
            return

        if self.es(TokenKind.IF):
            self.if_stmt()
            return

        if self.es(TokenKind.FOR):
            self.for_stmt()
            return

        if self.es(TokenKind.PRINT):
            self.print_stmt()
            return

        self.siguiente()

    # DECL_VAR → TIPO_DATO ID = EXPRESION
    def decl_var(self):
        # Guardamos la línea antes de consumir tokens.
        linea = self.actual().line

        tipo_variable = self.tipo_dato()

        nombre = self.actual().lexeme

        self.siguiente_si(TokenKind.ID)
        self.siguiente_si(TokenKind.ASSIGN)

        tipo_expresion = self.expresion()

        # ¿La variable ya existe?
        if nombre in self.tabla:
            self.error_declaracion(linea, f"La variable '{nombre}' ya fue declarada.")
            return

        # ¿Los tipos coinciden?
        if tipo_expresion is not None and tipo_variable != tipo_expresion:
            self.error_tipo(
                linea,
                f"La variable '{nombre}' "
                f"es {tipo_variable}, "
                f"pero se recibió {tipo_expresion}.",
            )

        # Se guarda incluso si hubo error de tipos.
        self.tabla[nombre] = tipo_variable

    # ASIGNACION → ID = EXPRESION
    def asignacion(self):
        # Guardamos la línea antes de consumir tokens.
        linea = self.actual().line

        nombre = self.actual().lexeme

        self.siguiente_si(TokenKind.ID)
        self.siguiente_si(TokenKind.ASSIGN)

        tipo_expresion = self.expresion()

        # ¿La variable existe?
        if nombre not in self.tabla:
            self.error_declaracion(
                linea, f"La variable '{nombre}' no ha sido declarada."
            )

            return

        tipo_variable = self.tabla[nombre]

        # ¿Los tipos coinciden?
        if tipo_expresion is not None and tipo_variable != tipo_expresion:
            self.error_tipo(
                linea,
                f"La variable '{nombre}' "
                f"es {tipo_variable}, "
                f"pero se asignó {tipo_expresion}.",
            )

    # IF → if EXPRESION { LISTA_DECL } [else { LISTA_DECL }]
    def if_stmt(self):
        linea = self.actual().line

        self.siguiente_si(TokenKind.IF)

        tipo_condicion = self.expresion()

        if tipo_condicion is not None and tipo_condicion != "bool":
            self.error_tipo(linea, "La condición del if debe ser bool.")

        self.siguiente_si(TokenKind.LBRACE)

        self.lista_decl()

        self.siguiente_si(TokenKind.RBRACE)

        if self.es(TokenKind.ELSE):
            self.siguiente()

            self.siguiente_si(TokenKind.LBRACE)

            self.lista_decl()

            self.siguiente_si(TokenKind.RBRACE)

    # FOR → for EXPRESION { LISTA_DECL }
    def for_stmt(self):
        linea = self.actual().line

        self.siguiente_si(TokenKind.FOR)

        tipo_condicion = self.expresion()

        if tipo_condicion is not None and tipo_condicion != "bool":
            self.error_tipo(linea, "La condición del for debe ser bool.")

        self.siguiente_si(TokenKind.LBRACE)

        self.lista_decl()

        self.siguiente_si(TokenKind.RBRACE)

    # PRINT → print ( EXPRESION )
    def print_stmt(self):
        self.siguiente_si(TokenKind.PRINT)

        self.siguiente_si(TokenKind.LPAREN)

        self.expresion()

        self.siguiente_si(TokenKind.RPAREN)

    # TIPO_DATO → int | bool
    def tipo_dato(self):
        if self.es(TokenKind.INT):
            self.siguiente()
            return "int"

        if self.es(TokenKind.BOOL):
            self.siguiente()
            return "bool"

        return None

    # EXPRESION → SUMA [ ( == | > | < ) SUMA ]
    def expresion(self):
        tipo = self.suma()

        # ==
        if self.es(TokenKind.EQ):
            linea = self.actual().line

            self.siguiente()

            tipo_derecha = self.suma()

            if tipo is None or tipo_derecha is None:
                return None

            if tipo != tipo_derecha:
                self.error_tipo(
                    linea, "Los dos lados de '==' deben tener el mismo tipo."
                )

                return None

            return "bool"

        # > o <
        if self.es(TokenKind.GREATER) or self.es(TokenKind.LESS):
            operador = self.actual().lexeme
            linea = self.actual().line

            self.siguiente()

            tipo_derecha = self.suma()

            if tipo is None or tipo_derecha is None:
                return None

            if tipo != "int" or tipo_derecha != "int":
                self.error_tipo(
                    linea, f"El operador '{operador}' requiere valores int."
                )

                return None

            return "bool"

        return tipo

    # SUMA → TERMINO [ ( @ | # ) TERMINO ]*
    def suma(self):
        tipo = self.termino()

        while self.es(TokenKind.AT) or self.es(TokenKind.HASH):
            operador = self.actual().lexeme
            linea = self.actual().line

            self.siguiente()

            tipo_derecha = self.termino()

            if tipo is None or tipo_derecha is None:
                tipo = None
                continue

            if tipo != "int" or tipo_derecha != "int":
                self.error_tipo(
                    linea, f"El operador '{operador}' requiere valores int."
                )

                tipo = None

            else:
                tipo = "int"

        return tipo

    # TERMINO → FACTOR [ ( & | | ) FACTOR ]*
    def termino(self):
        tipo = self.factor()

        while self.es(TokenKind.AMPERSAND) or self.es(TokenKind.PIPE):
            operador = self.actual().lexeme
            linea = self.actual().line

            self.siguiente()

            tipo_derecha = self.factor()

            if tipo is None or tipo_derecha is None:
                tipo = None
                continue

            if tipo != "int" or tipo_derecha != "int":
                self.error_tipo(
                    linea, f"El operador '{operador}' requiere valores int."
                )

                tipo = None

            else:
                tipo = "int"

        return tipo

    # FACTOR → ID | NUM | BOOL | ( EXPRESION )
    def factor(self):
        # ID
        if self.es(TokenKind.ID):
            nombre = self.actual().lexeme
            linea = self.actual().line

            self.siguiente()

            if nombre not in self.tabla:
                self.error_declaracion(
                    linea, f"La variable '{nombre}' no ha sido declarada."
                )

                return None

            return self.tabla[nombre]

        # NUM
        if self.es(TokenKind.NUM):
            self.siguiente()

            return "int"

        # true / false
        if self.es(TokenKind.TRUE) or self.es(TokenKind.FALSE):
            self.siguiente()

            return "bool"

        # ( EXPRESION )
        if self.es(TokenKind.LPAREN):
            self.siguiente()

            tipo = self.expresion()

            self.siguiente_si(TokenKind.RPAREN)

            return tipo

        return None

    def siguiente_si(self, tipo):
        if self.es(tipo):
            self.siguiente()

    def es(self, tipo):
        return self.actual().kind == tipo

    def actual(self):
        return self.tokens[self.indice]

    def siguiente(self):
        if self.indice < len(self.tokens) - 1:
            self.indice += 1

    def error_tipo(self, linea, mensaje):
        self.errores.append(f"Línea {linea}: ERROR DE TIPOS: {mensaje}")

    def error_declaracion(self, linea, mensaje):
        self.errores.append(f"Línea {linea}: ERROR DE DECLARACIÓN: {mensaje}")
