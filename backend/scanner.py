from tokens import Token, TokenKind

PALABRAS_RESERVADAS = {
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "for": TokenKind.FOR,
    "print": TokenKind.PRINT,
    "int": TokenKind.INT,
    "bool": TokenKind.BOOL,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
}


CARACTERES = {
    "{": TokenKind.LBRACE,
    "}": TokenKind.RBRACE,
    ";": TokenKind.SEMICOLON,
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
    "=": TokenKind.ASSIGN,
    ">": TokenKind.GREATER,
    "<": TokenKind.LESS,
    "@": TokenKind.AT,
    "#": TokenKind.HASH,
    "&": TokenKind.AMPERSAND,
    "|": TokenKind.PIPE,
}


def analizar_lexico(codigo):
    tokens = []
    errores = []

    i = 0
    linea = 1

    while i < len(codigo):
        caracter = codigo[i]

        # Espacios
        if caracter in " \t\r":
            i += 1
            continue

        # Salto de línea
        if caracter == "\n":
            linea += 1
            i += 1
            continue

        # Identificadores y palabras reservadas
        if caracter.isalpha():
            inicio = i

            while i < len(codigo) and codigo[i].isalnum():
                i += 1

            lexema = codigo[inicio:i]

            tipo = PALABRAS_RESERVADAS.get(
                lexema,
                TokenKind.ID,
            )

            tokens.append(
                Token(
                    tipo,
                    lexema,
                    linea,
                ),
            )

            continue

        # Números
        if caracter.isdigit():
            inicio = i

            while i < len(codigo) and codigo[i].isdigit():
                i += 1

            lexema = codigo[inicio:i]

            tokens.append(
                Token(
                    TokenKind.NUM,
                    lexema,
                    linea,
                ),
            )

            continue

        # Igual ==
        if caracter == "=" and i + 1 < len(codigo) and codigo[i + 1] == "=":
            tokens.append(
                Token(
                    TokenKind.EQ,
                    "==",
                    linea,
                ),
            )

            i += 2
            continue

        # Caracteres individuales
        if caracter in CARACTERES:
            tokens.append(
                Token(
                    CARACTERES[caracter],
                    caracter,
                    linea,
                ),
            )

            i += 1
            continue

        # Caracter inválido
        errores.append(f"Línea {linea}: Caracter inválido '{caracter}'.")

        tokens.append(
            Token(
                TokenKind.INVALID,
                caracter,
                linea,
            ),
        )

        i += 1

    # EOF
    tokens.append(
        Token(
            TokenKind.EOF,
            "EOF",
            linea,
        ),
    )

    return tokens, errores
