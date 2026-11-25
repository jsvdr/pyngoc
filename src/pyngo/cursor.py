from .tokens import Token, TokenKind


# Shared cursor: the token list and the current position.
# Parser, semantic analyzer, IR generator and code generator inherit these methods.
class TokenCursor:
    tokens: list[Token]
    position: int

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.position = 0

    def current_is(self, expected_kind: TokenKind) -> bool:
        return self.current_token().kind == expected_kind

    def current_token(self) -> Token:
        return self.tokens[self.position]

    def advance(self) -> None:
        # Never move past the last token, so we cannot leave the list.
        if self.position < len(self.tokens) - 1:
            self.position += 1

    def advance_if(self, expected_kind: TokenKind) -> None:
        if self.current_is(expected_kind):
            self.advance()
