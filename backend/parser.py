from tokens import Token, TokenKind


# Parser: lista_tokens -> Syntax OK o lista de errores. Solo revisa.
# Cada método calca una regla de gramatica.md, no devuelve nada.
class Parser:
    tokens: list[Token]
    posicion: int
    errores: list[str]

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.posicion = 0
        self.errores = []

    def analizar(self) -> tuple[bool, list[str]]:
        self.programa()

        if not self.token_actual_es(TokenKind.EOF):
            self.anotar_error("Se esperaba el final del programa.")

        if len(self.errores) == 0:
            return True, ["Syntax OK"]

        return False, self.errores

    # PROGRAMA → { LISTA_DECL }
    def programa(self) -> None:
        self.consumir(TokenKind.LBRACE, "Se esperaba '{'.")

        self.lista_decl()

        self.consumir(TokenKind.RBRACE, "Se esperaba '}'.")

    # LISTA_DECL → [ DECL ; ]*
    # Para en } o EOF para no leer de más.
    def lista_decl(self) -> None:
        while not self.token_actual_es(TokenKind.RBRACE) and not self.token_actual_es(
            TokenKind.EOF
        ):
            self.decl()

            self.consumir(TokenKind.SEMICOLON, "Se esperaba ';'.")

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

        self.anotar_error(f"Declaración no válida: '{self.token_actual().lexeme}'.")

        # Si no se reconoce, se avanza para no atorarse.
        self.avanzar()

    # DECL_VAR → TIPO_DATO ID = EXPRESION
    def decl_var(self) -> None:
        self.tipo_dato()

        self.consumir(TokenKind.ID, "Se esperaba un ID.")

        self.consumir(TokenKind.ASSIGN, "Se esperaba '='.")

        self.expresion()

    # ASIGNACION → ID = EXPRESION
    def asignacion(self) -> None:
        self.consumir(TokenKind.ID, "Se esperaba un ID.")

        self.consumir(TokenKind.ASSIGN, "Se esperaba '='.")

        self.expresion()

    # IF → if EXPRESION { LISTA_DECL } [else { LISTA_DECL }]
    def if_stmt(self) -> None:
        self.consumir(TokenKind.IF, "Se esperaba 'if'.")

        self.expresion()

        self.consumir(TokenKind.LBRACE, "Se esperaba '{'.")

        self.lista_decl()

        self.consumir(TokenKind.RBRACE, "Se esperaba '}'.")

        if self.token_actual_es(TokenKind.ELSE):
            self.avanzar()

            self.consumir(TokenKind.LBRACE, "Se esperaba '{' después de 'else'.")

            self.lista_decl()

            self.consumir(TokenKind.RBRACE, "Se esperaba '}'.")

    # FOR → for EXPRESION { LISTA_DECL }
    def for_stmt(self) -> None:
        self.consumir(TokenKind.FOR, "Se esperaba 'for'.")

        self.expresion()

        self.consumir(TokenKind.LBRACE, "Se esperaba '{'.")

        self.lista_decl()

        self.consumir(TokenKind.RBRACE, "Se esperaba '}'.")

    # PRINT → print ( EXPRESION )
    def print_stmt(self) -> None:
        self.consumir(TokenKind.PRINT, "Se esperaba 'print'.")

        self.consumir(TokenKind.LPAREN, "Se esperaba '('.")

        self.expresion()

        self.consumir(TokenKind.RPAREN, "Se esperaba ')'.")

    # TIPO_DATO → int | bool
    def tipo_dato(self) -> None:
        if self.token_actual_es(TokenKind.INT) or self.token_actual_es(TokenKind.BOOL):
            self.avanzar()
            return

        self.anotar_error("Se esperaba 'int' o 'bool'.")

    # EXPRESION → SUMA [ ( == | > | < ) SUMA ]
    def expresion(self) -> None:
        self.suma()

        if (
            self.token_actual_es(TokenKind.EQ)
            or self.token_actual_es(TokenKind.GREATER)
            or self.token_actual_es(TokenKind.LESS)
        ):
            self.avanzar()
            self.suma()

    # SUMA → TERMINO [ ( @ | # ) TERMINO ]*
    def suma(self) -> None:
        self.termino()

        while self.token_actual_es(TokenKind.AT) or self.token_actual_es(
            TokenKind.HASH
        ):
            self.avanzar()
            self.termino()

    # TERMINO → FACTOR [ ( & | | ) FACTOR ]*
    def termino(self) -> None:
        self.factor()

        while self.token_actual_es(TokenKind.AMPERSAND) or self.token_actual_es(
            TokenKind.PIPE
        ):
            self.avanzar()
            self.factor()

    # FACTOR → ID | NUM | BOOL | ( EXPRESION )
    def factor(self) -> None:
        if self.token_actual_es(TokenKind.ID):
            self.avanzar()
            return

        if self.token_actual_es(TokenKind.NUM):
            self.avanzar()
            return

        if self.token_actual_es(TokenKind.TRUE):
            self.avanzar()
            return

        if self.token_actual_es(TokenKind.FALSE):
            self.avanzar()
            return

        if self.token_actual_es(TokenKind.LPAREN):
            self.avanzar()

            self.expresion()

            self.consumir(TokenKind.RPAREN, "Se esperaba ')'.")

            return

        self.anotar_error(
            f"Se esperaba un FACTOR, pero se encontró '{self.token_actual().lexeme}'."
        )

    # Si es lo esperado avanza, si no anota el error.
    def consumir(self, kind_esperado: TokenKind, mensaje_error: str) -> None:
        if self.token_actual_es(kind_esperado):
            self.avanzar()
            return

        self.anotar_error(mensaje_error)

    def token_actual_es(self, kind_esperado: TokenKind) -> bool:
        return self.token_actual().kind == kind_esperado

    def token_actual(self) -> Token:
        return self.tokens[self.posicion]

    def avanzar(self) -> None:
        # No pasa del último para no salirse de la lista.
        if self.posicion < len(self.tokens) - 1:
            self.posicion += 1

    def anotar_error(self, texto_error: str) -> None:
        token = self.token_actual()

        self.errores.append(f"Línea {token.line}: {texto_error}")
