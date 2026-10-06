from enum import IntEnum


# Tokens: qué es cada pedazo del texto (int, if, @, ...).
# No revisa nada, solo guarda kind + lexeme + line.
class TokenKind(IntEnum):
    EOF = 0

    IF = 1
    ELSE = 2
    FOR = 3
    PRINT = 4
    INT = 5
    BOOL = 6
    TRUE = 7
    FALSE = 8

    ID = 9
    NUM = 10

    EQ = 11
    GREATER = 12
    LESS = 13
    ASSIGN = 14

    AT = 15
    HASH = 16
    AMPERSAND = 17
    PIPE = 18

    LBRACE = 19
    RBRACE = 20
    SEMICOLON = 21
    LPAREN = 22
    RPAREN = 23

    INVALID = 24


class Token:
    kind: TokenKind
    lexeme: str
    line: int

    def __init__(self, kind: TokenKind, lexeme: str, line: int) -> None:
        self.kind = kind
        self.lexeme = lexeme
        self.line = line

    def __str__(self) -> str:
        return f"<TKN {self.kind.name} {self.lexeme}>"

    def __repr__(self) -> str:
        return str(self)
