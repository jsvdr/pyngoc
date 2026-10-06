from tokens import Token, TokenKind

# Scanner: texto_fuente -> (lista_tokens, lista_errores). Nunca frena.
# Siempre devuelve EOF al final para que el parser sepa dónde acaba.
PALABRAS_RESERVADAS: dict[str, TokenKind] = {
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "for": TokenKind.FOR,
    "print": TokenKind.PRINT,
    "int": TokenKind.INT,
    "bool": TokenKind.BOOL,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
}


CARACTERES: dict[str, TokenKind] = {
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


def analizar_lexico(texto_fuente: str) -> tuple[list[Token], list[str]]:
    tokens: list[Token] = []
    errores: list[str] = []

    pos = 0
    numero_linea = 1

    while pos < len(texto_fuente):
        caracter = texto_fuente[pos]

        # Los espacios no son tokens, se saltan.
        if caracter in " \t\r":
            pos += 1
            continue

        # Solo \n sube la línea, así el error dice la línea real.
        if caracter == "\n":
            numero_linea += 1
            pos += 1
            continue

        # Identificadores y palabras reservadas
        if caracter.isalpha():
            pos_inicio = pos

            while pos < len(texto_fuente) and texto_fuente[pos].isalnum():
                pos += 1

            palabra = texto_fuente[pos_inicio:pos]

            kind = PALABRAS_RESERVADAS.get(
                palabra,
                TokenKind.ID,
            )

            tokens.append(
                Token(
                    kind,
                    palabra,
                    numero_linea,
                ),
            )

            continue

        # Números
        if caracter.isdigit():
            pos_inicio = pos

            while pos < len(texto_fuente) and texto_fuente[pos].isdigit():
                pos += 1

            texto_numero = texto_fuente[pos_inicio:pos]

            tokens.append(
                Token(
                    TokenKind.NUM,
                    texto_numero,
                    numero_linea,
                ),
            )

            continue

        # "==" son 2 letras: se mira pos+1 o se confunde con "=".
        if (
            caracter == "="
            and pos + 1 < len(texto_fuente)
            and texto_fuente[pos + 1] == "="
        ):
            tokens.append(
                Token(
                    TokenKind.EQ,
                    "==",
                    numero_linea,
                ),
            )

            pos += 2
            continue

        # Caracteres individuales
        if caracter in CARACTERES:
            tokens.append(
                Token(
                    CARACTERES[caracter],
                    caracter,
                    numero_linea,
                ),
            )

            pos += 1
            continue

        # Lo raro se guarda y se sigue para no frenar todo.
        errores.append(f"Línea {numero_linea}: Caracter inválido '{caracter}'.")

        tokens.append(
            Token(
                TokenKind.INVALID,
                caracter,
                numero_linea,
            ),
        )

        pos += 1

    # EOF marca el final, el parser lo exige.
    tokens.append(
        Token(
            TokenKind.EOF,
            "EOF",
            numero_linea,
        ),
    )

    return tokens, errores
