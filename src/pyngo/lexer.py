from .tokens import Token, TokenKind

# Lexer: source_text -> (token_list, error_list). It never stops early.
# It always appends EOF at the end so the parser knows where the program ends.

# An identifier is a lowercase letter followed by lowercase letters or digits,
# ASCII only. We deliberately do NOT use str.isalpha()/str.isalnum(): those
# accept 'ñ', 'á' or '²', and such names would break compatibility.
LETTERS = set("abcdefghijklmnopqrstuvwxyz")
DIGITS = set("0123456789")
ALPHANUMERIC = LETTERS | DIGITS

RESERVED_WORDS: dict[str, TokenKind] = {
    "if": TokenKind.IF,
    "while": TokenKind.WHILE,
    "print": TokenKind.PRINT,
    "int": TokenKind.INT,
    "bool": TokenKind.BOOL,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
}


CHARACTERS: dict[str, TokenKind] = {
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


def tokenize(source_text: str) -> tuple[list[Token], list[str]]:
    tokens: list[Token] = []
    errors: list[str] = []

    position = 0
    line_number = 1

    while position < len(source_text):
        character = source_text[position]

        # Spaces are not tokens; skip them.
        if character in " \t\r":
            position += 1
            continue

        # Only \n advances the line, so the error reports the real line.
        if character == "\n":
            line_number += 1
            position += 1
            continue

        # Identifiers and reserved words
        if character in LETTERS:
            start = position

            while position < len(source_text) and source_text[position] in ALPHANUMERIC:
                position += 1

            word = source_text[start:position]

            kind = RESERVED_WORDS.get(word, TokenKind.ID)

            tokens.append(Token(kind, word, line_number))

            continue

        # Numbers
        if character in DIGITS:
            start = position

            while position < len(source_text) and source_text[position] in DIGITS:
                position += 1

            number_text = source_text[start:position]

            tokens.append(Token(TokenKind.NUM, number_text, line_number))

            continue

        # "==" is two characters: check position+1 or it looks like "=".
        if character == "=" and position + 1 < len(source_text) and source_text[position + 1] == "=":
            tokens.append(Token(TokenKind.EQ, "==", line_number))

            position += 2
            continue

        # Single characters
        if character in CHARACTERS:
            tokens.append(Token(CHARACTERS[character], character, line_number))

            position += 1
            continue

        # Anything unknown is recorded and skipped, so we do not stop everything.
        errors.append(f"Line {line_number}: Invalid character '{character}'.")

        tokens.append(Token(TokenKind.INVALID, character, line_number))

        position += 1

    # EOF marks the end; the parser requires it.
    tokens.append(Token(TokenKind.EOF, "EOF", line_number))

    return tokens, errors
