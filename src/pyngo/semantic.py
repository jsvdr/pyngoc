from collections.abc import Callable

from .cursor import TokenCursor
from .tokens import Token, TokenKind


# Semantic analyzer: token_list -> Semantic OK or errors. Returns int/bool/None.
# None = an earlier error already happened, so we do not cascade another one.
class SemanticAnalyzer(TokenCursor):
    errors: list[str]
    # variable_name -> "int" or "bool"
    symbol_table: dict[str, str]

    def __init__(self, tokens: list[Token]) -> None:
        super().__init__(tokens)
        self.errors = []
        self.symbol_table = {}

    def analyze(self) -> tuple[bool, list[str]]:
        self.program()

        if len(self.errors) == 0:
            return True, ["Semantic OK"]

        return False, self.errors

    # PROGRAM → { DECL_LIST }
    def program(self) -> None:
        self.advance_if(TokenKind.LBRACE)

        self.decl_list()

        self.advance_if(TokenKind.RBRACE)

    # DECL_LIST → [ DECL ; ]*
    def decl_list(self) -> None:
        while not self.current_is(TokenKind.RBRACE) and not self.current_is(TokenKind.EOF):
            self.decl()

            self.advance_if(TokenKind.SEMICOLON)

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
            self.advance()

    # VAR_DECL → DATA_TYPE ID = EXPRESSION
    def var_decl(self) -> None:
        # Capture it BEFORE reading the rest, or it would point at the ";".
        line_number = self.current_token().line

        declared_type = self.data_type()

        # Without a type we cannot store anything. This should not happen:
        # var_decl is only called when int/bool is in front.
        if declared_type is None:
            return

        variable_name = self.current_token().lexeme

        self.advance_if(TokenKind.ID)
        self.advance_if(TokenKind.ASSIGN)

        found_type = self.expression()

        # Does the variable already exist?
        if variable_name in self.symbol_table:
            self.declaration_error(line_number, f"Variable '{variable_name}' has already been declared.")
            return

        # Do the types match?
        if found_type is not None and declared_type != found_type:
            self.type_error(
                line_number,
                f"Variable '{variable_name}' is {declared_type}, but got {found_type}.",
            )

        # It is stored even after a type error.
        self.symbol_table[variable_name] = declared_type

    # ASSIGNMENT → ID = EXPRESSION
    def assignment(self) -> None:
        # Capture it BEFORE reading the rest, or it would point at the ";".
        line_number = self.current_token().line

        variable_name = self.current_token().lexeme

        self.advance_if(TokenKind.ID)
        self.advance_if(TokenKind.ASSIGN)

        found_type = self.expression()

        # Does the variable exist?
        if variable_name not in self.symbol_table:
            self.declaration_error(line_number, f"Variable '{variable_name}' has not been declared.")

            return

        declared_type = self.symbol_table[variable_name]

        # Do the types match?
        if found_type is not None and declared_type != found_type:
            self.type_error(
                line_number,
                f"Variable '{variable_name}' is {declared_type}, but was assigned {found_type}.",
            )

    # IF → if EXPRESSION { DECL_LIST }
    def if_stmt(self) -> None:
        line_number = self.current_token().line

        self.advance_if(TokenKind.IF)

        condition_type = self.expression()

        if condition_type is not None and condition_type != "bool":
            self.type_error(line_number, "The if condition must be bool.")

        self.advance_if(TokenKind.LBRACE)

        self.decl_list()

        self.advance_if(TokenKind.RBRACE)

    # WHILE → while EXPRESSION { DECL_LIST }
    def while_stmt(self) -> None:
        line_number = self.current_token().line

        self.advance_if(TokenKind.WHILE)

        condition_type = self.expression()

        if condition_type is not None and condition_type != "bool":
            self.type_error(line_number, "The while condition must be bool.")

        self.advance_if(TokenKind.LBRACE)

        self.decl_list()

        self.advance_if(TokenKind.RBRACE)

    # PRINT → print ( ID )   only int variables that are already declared
    def print_stmt(self) -> None:
        self.advance_if(TokenKind.PRINT)
        self.advance_if(TokenKind.LPAREN)

        token = self.current_token()
        line_number = token.line
        if token.kind != TokenKind.ID:
            self.declaration_error(line_number, "print only accepts a variable.")
        elif token.lexeme not in self.symbol_table:
            self.declaration_error(line_number, f"Variable '{token.lexeme}' has not been declared.")
        elif self.symbol_table[token.lexeme] != "int":
            current_type = self.symbol_table[token.lexeme]
            self.type_error(line_number, f"print only accepts int, but '{token.lexeme}' is {current_type}.")
        self.advance_if(TokenKind.ID)

        self.advance_if(TokenKind.RPAREN)

    # DATA_TYPE → int | bool
    def data_type(self) -> str | None:
        data_type = {TokenKind.INT: "int", TokenKind.BOOL: "bool"}.get(self.current_token().kind)
        if data_type:
            self.advance()
        return data_type

    # EXPRESSION → SUM [ ( == | > | < ) SUM ]
    def expression(self) -> str | None:
        first_type = self.sum()

        # ==
        if self.current_is(TokenKind.EQ):
            line_number = self.current_token().line

            self.advance()

            second_type = self.sum()

            if first_type is None or second_type is None:
                return None

            if first_type != second_type:
                self.type_error(line_number, "Both sides of '==' must have the same type.")

                return None

            return "bool"

        # > or <
        if self.current_is(TokenKind.GREATER) or self.current_is(TokenKind.LESS):
            operator = self.current_token().lexeme
            line_number = self.current_token().line

            self.advance()

            second_type = self.sum()

            if first_type is None or second_type is None:
                return None

            if first_type != "int" or second_type != "int":
                self.type_error(line_number, f"Operator '{operator}' requires int values.")

                return None

            return "bool"

        return first_type

    # SUM → TERM [ ( @ | # ) TERM ]*
    # Folded on the fly, without a tree: hold one value, read the next.
    def sum(self) -> str | None:
        return self.check_operation((TokenKind.AT, TokenKind.HASH), self.term)

    # TERM → FACTOR [ ( & | | ) FACTOR ]*
    # Folded on the fly, without a tree: hold one value, read the next.
    def term(self) -> str | None:
        return self.check_operation(
            (TokenKind.AMPERSAND, TokenKind.PIPE),
            self.factor,
        )

    # Walk a chain of same-level operators (@ # or & |).
    # Each side must be int; otherwise record the error for that line.
    def check_operation(
        self,
        operator_kinds: tuple[TokenKind, ...],
        read_operand: Callable[[], str | None],
    ) -> str | None:
        accumulated_type = read_operand()

        while self.current_token().kind in operator_kinds:
            operator = self.current_token().lexeme
            line_number = self.current_token().line

            self.advance()

            new_type = read_operand()

            if accumulated_type is None or new_type is None:
                accumulated_type = None
                continue

            if accumulated_type != "int" or new_type != "int":
                self.type_error(line_number, f"Operator '{operator}' requires int values.")

                accumulated_type = None

            else:
                accumulated_type = "int"

        return accumulated_type

    # FACTOR → ID | NUM | BOOL | ( EXPRESSION )
    def factor(self) -> str | None:
        # ID
        if self.current_is(TokenKind.ID):
            variable_name = self.current_token().lexeme
            line_number = self.current_token().line

            self.advance()

            if variable_name not in self.symbol_table:
                self.declaration_error(
                    line_number,
                    f"Variable '{variable_name}' has not been declared.",
                )

                return None

            return self.symbol_table[variable_name]

        # NUM
        if self.current_is(TokenKind.NUM):
            if int(self.current_token().lexeme) > 0xFFFF:
                self.type_error(
                    self.current_token().line,
                    "The number does not fit in 16 bits (0..65535).",
                )
            self.advance()

            return "int"

        # true / false
        if self.current_is(TokenKind.TRUE) or self.current_is(TokenKind.FALSE):
            self.advance()

            return "bool"

        # ( EXPRESSION ): the inner expression decides the type.
        if self.current_is(TokenKind.LPAREN):
            self.advance()

            inner_type = self.expression()

            self.advance_if(TokenKind.RPAREN)

            return inner_type

        return None

    def type_error(self, line_number: int, error_text: str) -> None:
        self.errors.append(f"Line {line_number}: TYPE ERROR: {error_text}")

    def declaration_error(self, line_number: int, error_text: str) -> None:
        self.errors.append(f"Line {line_number}: DECLARATION ERROR: {error_text}")
