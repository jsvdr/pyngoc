from .cursor import TokenCursor
from .tokens import Token, TokenKind


# Parser: token_list -> Syntax OK or error list. It only validates.
# Each method mirrors one rule from grammar.md and returns nothing.
class Parser(TokenCursor):
    errors: list[str]

    def __init__(self, tokens: list[Token]) -> None:
        super().__init__(tokens)
        self.errors = []

    def analyze(self) -> tuple[bool, list[str]]:
        self.program()

        if not self.current_is(TokenKind.EOF):
            self.note_error("Expected end of program.")

        if len(self.errors) == 0:
            return True, ["Syntax OK"]

        return False, self.errors

    # PROGRAM → { DECL_LIST }
    def program(self) -> None:
        self.consume(TokenKind.LBRACE, "Expected '{'.")

        self.decl_list()

        self.consume(TokenKind.RBRACE, "Expected '}'.")

    # DECL_LIST → [ DECL ; ]*
    # Stops at } or EOF so it does not read past the end.
    def decl_list(self) -> None:
        while not self.current_is(TokenKind.RBRACE) and not self.current_is(TokenKind.EOF):
            self.decl()

            self.consume(TokenKind.SEMICOLON, "Expected ';'.")

    # DECL → VAR_DECL | ASSIGNMENT | IF | WHILE | PRINT
    def decl(self) -> None:
        if self.current_is(TokenKind.INT) or self.current_is(TokenKind.BOOL):
            self.var_decl()
        elif self.current_is(TokenKind.ID):
            self.assignment()
        elif self.current_is(TokenKind.IF):
            self.if_stmt()
        elif self.current_is(TokenKind.WHILE):
            self.while_stmt()
        elif self.current_is(TokenKind.PRINT):
            self.print_stmt()
        else:
            self.note_error(f"Invalid declaration: '{self.current_token().lexeme}'.")
            self.advance()

    # VAR_DECL → DATA_TYPE ID = EXPRESSION
    def var_decl(self) -> None:
        self.data_type()

        self.consume(TokenKind.ID, "Expected an ID.")

        self.consume(TokenKind.ASSIGN, "Expected '='.")

        self.expression()

    # ASSIGNMENT → ID = EXPRESSION
    def assignment(self) -> None:
        self.consume(TokenKind.ID, "Expected an ID.")

        self.consume(TokenKind.ASSIGN, "Expected '='.")

        self.expression()

    # IF → if EXPRESSION { DECL_LIST }
    def if_stmt(self) -> None:
        self.consume(TokenKind.IF, "Expected 'if'.")

        self.expression()

        self.consume(TokenKind.LBRACE, "Expected '{'.")

        self.decl_list()

        self.consume(TokenKind.RBRACE, "Expected '}'.")

    # WHILE → while EXPRESSION { DECL_LIST }
    def while_stmt(self) -> None:
        self.consume(TokenKind.WHILE, "Expected 'while'.")

        self.expression()

        self.consume(TokenKind.LBRACE, "Expected '{'.")

        self.decl_list()

        self.consume(TokenKind.RBRACE, "Expected '}'.")

    # PRINT → print ( ID )
    def print_stmt(self) -> None:
        self.consume(TokenKind.PRINT, "Expected 'print'.")

        self.consume(TokenKind.LPAREN, "Expected '('.")

        self.consume(TokenKind.ID, "print only accepts a variable.")

        self.consume(TokenKind.RPAREN, "Expected ')'.")

    # DATA_TYPE → int | bool
    def data_type(self) -> None:
        if self.current_is(TokenKind.INT) or self.current_is(TokenKind.BOOL):
            self.advance()
            return

        self.note_error("Expected 'int' or 'bool'.")

    # EXPRESSION → SUM [ ( == | > | < ) SUM ]
    def expression(self) -> None:
        self.sum()

        if (
            self.current_is(TokenKind.EQ)
            or self.current_is(TokenKind.GREATER)
            or self.current_is(TokenKind.LESS)
        ):
            self.advance()
            self.sum()

    # SUM → TERM [ ( @ | # ) TERM ]*
    def sum(self) -> None:
        self.term()

        while self.current_is(TokenKind.AT) or self.current_is(TokenKind.HASH):
            self.advance()
            self.term()

    # TERM → FACTOR [ ( & | | ) FACTOR ]*
    def term(self) -> None:
        self.factor()

        while self.current_is(TokenKind.AMPERSAND) or self.current_is(TokenKind.PIPE):
            self.advance()
            self.factor()

    # FACTOR → ID | NUM | BOOL | ( EXPRESSION )
    def factor(self) -> None:
        if self.current_token().kind in (
            TokenKind.ID,
            TokenKind.NUM,
            TokenKind.TRUE,
            TokenKind.FALSE,
        ):
            self.advance()
            return

        if self.current_is(TokenKind.LPAREN):
            self.advance()

            self.expression()

            self.consume(TokenKind.RPAREN, "Expected ')'.")

            return

        self.note_error(f"Expected a FACTOR, but found '{self.current_token().lexeme}'.")

    # If it is what we expect, advance; otherwise record the error.
    def consume(self, expected_kind: TokenKind, error_message: str) -> None:
        if self.current_is(expected_kind):
            self.advance()
            return

        self.note_error(error_message)

    def note_error(self, error_text: str) -> None:
        token = self.current_token()

        self.errors.append(f"Line {token.line}: {error_text}")
