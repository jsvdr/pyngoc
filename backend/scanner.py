from tokens import Token, TokenKind

KEYWORDS = {
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "for": TokenKind.FOR,
    "print": TokenKind.PRINT,
    "int": TokenKind.INT,
    "bool": TokenKind.BOOL,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
}


class Scanner:
    def __init__(self, codigo):
        self.codigo = codigo
        self.tokens = []
        self.errores = []

        self.indice = 0
        self.linea = 1

    def analizar(self):
        while self.indice < len(self.codigo):
            char = self.codigo[self.indice]

            # Espacios
            if char.isspace():
                if char == "\n":
                    self.linea += 1

                self.indice += 1
                continue

            # ID o palabra reservada
            if char.isalpha():
                self.leer_palabra()
                continue

            # NUM
            if char.isdigit():
                self.leer_numero()
                continue

            # ==
            if self.codigo[self.indice : self.indice + 2] == "==":
                self.agregar_token(TokenKind.EQ, "==")
                self.indice += 2
                continue

            # >
            if char == ">":
                self.agregar_token(TokenKind.GREATER, ">")
                self.indice += 1
                continue

            # <
            if char == "<":
                self.agregar_token(TokenKind.LESS, "<")
                self.indice += 1
                continue

            # =
            if char == "=":
                self.agregar_token(TokenKind.ASSIGN, "=")
                self.indice += 1
                continue

            # @
            if char == "@":
                self.agregar_token(TokenKind.AT, "@")
                self.indice += 1
                continue

            # #
            if char == "#":
                self.agregar_token(TokenKind.HASH, "#")
                self.indice += 1
                continue

            # &
            if char == "&":
                self.agregar_token(TokenKind.AMPERSAND, "&")
                self.indice += 1
                continue

            # |
            if char == "|":
                self.agregar_token(TokenKind.PIPE, "|")
                self.indice += 1
                continue

            # {
            if char == "{":
                self.agregar_token(TokenKind.LBRACE, "{")
                self.indice += 1
                continue

            # }
            if char == "}":
                self.agregar_token(TokenKind.RBRACE, "}")
                self.indice += 1
                continue

            # ;
            if char == ";":
                self.agregar_token(TokenKind.SEMICOLON, ";")
                self.indice += 1
                continue

            # (
            if char == "(":
                self.agregar_token(TokenKind.LPAREN, "(")
                self.indice += 1
                continue

            # )
            if char == ")":
                self.agregar_token(TokenKind.RPAREN, ")")
                self.indice += 1
                continue

            # Caracter inválido
            self.errores.append(f"Línea {self.linea}: Caracter inválido '{char}'")

            self.indice += 1

        self.tokens.append(Token(TokenKind.EOF, "", self.linea))

        return self.tokens, self.errores

    def leer_palabra(self):
        inicio = self.indice

        while self.indice < len(self.codigo) and self.codigo[self.indice].isalnum():
            self.indice += 1

        lexema = self.codigo[inicio : self.indice]

        if lexema in KEYWORDS:
            tipo = KEYWORDS[lexema]
        else:
            tipo = TokenKind.ID

        self.agregar_token(tipo, lexema)

    def leer_numero(self):
        inicio = self.indice

        while self.indice < len(self.codigo) and self.codigo[self.indice].isdigit():
            self.indice += 1

        lexema = self.codigo[inicio : self.indice]

        self.agregar_token(TokenKind.NUM, lexema)

    def agregar_token(self, tipo, lexema):
        self.tokens.append(Token(tipo, lexema, self.linea))
