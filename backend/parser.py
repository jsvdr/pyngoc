from tokens import TokenKind


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.indice = 0
        self.errores = []

    def analizar(self):
        self.programa()

        if not self.es(TokenKind.EOF):
            self.error("Se esperaba el final del programa.")

        if len(self.errores) == 0:
            return True, ["Syntax OK"]

        return False, self.errores

    # PROGRAMA → { LISTA_DECL }
    def programa(self):
        self.consumir(TokenKind.LBRACE, "Se esperaba '{'.")

        self.lista_decl()

        self.consumir(TokenKind.RBRACE, "Se esperaba '}'.")

    # LISTA_DECL → [ DECL ; ]*
    def lista_decl(self):
        while not self.es(TokenKind.RBRACE) and not self.es(TokenKind.EOF):
            self.decl()

            self.consumir(TokenKind.SEMICOLON, "Se esperaba ';'.")

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

        self.error(f"Declaración no válida: '{self.actual().lexeme}'.")

        self.siguiente()

    # DECL_VAR → TIPO_DATO ID = EXPRESION
    def decl_var(self):
        self.tipo_dato()

        self.consumir(TokenKind.ID, "Se esperaba un ID.")

        self.consumir(TokenKind.ASSIGN, "Se esperaba '='.")

        self.expresion()

    # ASIGNACION → ID = EXPRESION
    def asignacion(self):
        self.consumir(TokenKind.ID, "Se esperaba un ID.")

        self.consumir(TokenKind.ASSIGN, "Se esperaba '='.")

        self.expresion()

    # IF → if EXPRESION { LISTA_DECL } [else { LISTA_DECL }]
    def if_stmt(self):
        self.consumir(TokenKind.IF, "Se esperaba 'if'.")

        self.expresion()

        self.consumir(TokenKind.LBRACE, "Se esperaba '{'.")

        self.lista_decl()

        self.consumir(TokenKind.RBRACE, "Se esperaba '}'.")

        if self.es(TokenKind.ELSE):
            self.siguiente()

            self.consumir(TokenKind.LBRACE, "Se esperaba '{' después de 'else'.")

            self.lista_decl()

            self.consumir(TokenKind.RBRACE, "Se esperaba '}'.")

    # FOR → for EXPRESION { LISTA_DECL }
    def for_stmt(self):
        self.consumir(TokenKind.FOR, "Se esperaba 'for'.")

        self.expresion()

        self.consumir(TokenKind.LBRACE, "Se esperaba '{'.")

        self.lista_decl()

        self.consumir(TokenKind.RBRACE, "Se esperaba '}'.")

    # PRINT → print ( EXPRESION )
    def print_stmt(self):
        self.consumir(TokenKind.PRINT, "Se esperaba 'print'.")

        self.consumir(TokenKind.LPAREN, "Se esperaba '('.")

        self.expresion()

        self.consumir(TokenKind.RPAREN, "Se esperaba ')'.")

    # TIPO_DATO → int | bool
    def tipo_dato(self):

        if self.es(TokenKind.INT) or self.es(TokenKind.BOOL):
            self.siguiente()
            return

        self.error("Se esperaba 'int' o 'bool'.")

    # EXPRESION → SUMA [ ( == | > | < ) SUMA ]
    def expresion(self):
        self.suma()

        if (
            self.es(TokenKind.EQ)
            or self.es(TokenKind.GREATER)
            or self.es(TokenKind.LESS)
        ):
            self.siguiente()
            self.suma()

    # SUMA → TERMINO [ ( @ | # ) TERMINO ]*
    def suma(self):
        self.termino()

        while self.es(TokenKind.AT) or self.es(TokenKind.HASH):
            self.siguiente()
            self.termino()

    # TERMINO → FACTOR [ ( & | | ) FACTOR ]*
    def termino(self):
        self.factor()

        while self.es(TokenKind.AMPERSAND) or self.es(TokenKind.PIPE):
            self.siguiente()
            self.factor()

    # FACTOR → ID | NUM | BOOL | ( EXPRESION )
    def factor(self):

        if self.es(TokenKind.ID):
            self.siguiente()
            return

        if self.es(TokenKind.NUM):
            self.siguiente()
            return

        if self.es(TokenKind.TRUE):
            self.siguiente()
            return

        if self.es(TokenKind.FALSE):
            self.siguiente()
            return

        if self.es(TokenKind.LPAREN):
            self.siguiente()

            self.expresion()

            self.consumir(TokenKind.RPAREN, "Se esperaba ')'.")

            return

        self.error(f"Se esperaba un FACTOR, pero se encontró '{self.actual().lexeme}'.")

    def consumir(self, tipo, mensaje):
        if self.es(tipo):
            self.siguiente()
            return

        self.error(mensaje)

    def es(self, tipo):
        return self.actual().kind == tipo

    def actual(self):
        return self.tokens[self.indice]

    def siguiente(self):
        if self.indice < len(self.tokens) - 1:
            self.indice += 1

    def error(self, mensaje):
        token = self.actual()

        self.errores.append(f"Línea {token.line}: {mensaje}")
