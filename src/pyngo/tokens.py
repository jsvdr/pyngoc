from dataclasses import dataclass
from enum import IntEnum
from typing import override


# Tokens: what each piece of the source text is (int, if, @, ...).
# It checks nothing; it only stores kind + lexeme + line.
class TokenKind(IntEnum):
    EOF = 0

    IF = 1
    WHILE = 3
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


@dataclass
class Token:
    kind: TokenKind
    lexeme: str
    line: int

    @override
    def __str__(self) -> str:
        return f"<TKN {self.kind.name} {self.lexeme}>"

    @override
    def __repr__(self) -> str:
        return str(self)
