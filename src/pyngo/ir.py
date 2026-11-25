# IR: symbol table + tokens -> rows with 3 fields (Name, Operator, Attribute).
# Every expression is computed in AX and only simple operands are allowed
# (variable, number or true/false). Bools are DB: loaded into AL with AH = 0.
from .cursor import TokenCursor
from .tokens import Token
from .tokens import TokenKind as T


class IRError(Exception):
    """A construct that this simple version of the generator cannot produce."""


HEADER = [
    ("", "TITLE", "Pyngo"),
    ("", ".MODEL", "Small"),
    ("", ".486", ""),
    ("", ".STACK", ""),
    ("", "", ""),
    ("", ".DATA", ""),
]
CODE = [
    ("", "", ""),
    ("", ".CODE", ""),
    ("MAIN", "PROC", "FAR"),
    ("", ".STARTUP", ""),
    ("", "", ""),
]
FOOTER = [
    ("", "", ""),
    ("", ".EXIT", ""),
    ("MAIN", "ENDP", ""),
    ("", "", ""),
    ("", "END", ""),
]

JUMP_IF_FALSE = {T.LESS: "JAE", T.GREATER: "JBE", T.EQ: "JNE"}  # unsigned, same as object code
SET_IF_TRUE = {T.EQ: "SETE", T.GREATER: "SETA", T.LESS: "SETB"}
FORBIDDEN_AFTER_SUM = (T.AMPERSAND, T.PIPE)
FORBIDDEN_AFTER_COMPARISON = (T.AT, T.HASH, T.AMPERSAND, T.PIPE)


class IRGenerator(TokenCursor):
    def __init__(self, tokens: list[Token], symbol_table: dict[str, str]) -> None:
        super().__init__(tokens)
        self.rows: list[tuple[str, str, str]] = []
        self.label_number = 0
        self.symbol_table = symbol_table

    # ---------- statements ----------

    def block(self) -> None:  # { DECL_LIST }: used by the program, if and while
        self.advance_if(T.LBRACE)
        while not self.current_is(T.RBRACE) and not self.current_is(T.EOF):
            self.decl()
            self.advance_if(T.SEMICOLON)
        self.advance_if(T.RBRACE)

    def decl(self) -> None:
        kind = self.current_token().kind
        if kind == T.IF:
            self.if_stmt()
        elif kind == T.WHILE:
            self.while_stmt()
        elif kind == T.PRINT:
            self.print_stmt()
        else:
            self.assignment()  # VAR_DECL and ASSIGNMENT generate the same code

    def assignment(self) -> None:  # [int | bool] ID = EXPRESSION
        if self.current_token().kind in (T.INT, T.BOOL):
            self.advance()
        name = self.current_token().lexeme
        self.advance()  # ID
        self.advance()  # =
        self.expression()
        self.emit(f"MOV {name}, {'AL' if self.symbol_table.get(name) == 'bool' else 'AX'}")

    # Jump to false_label if the condition is false. A simple comparison (a < b)
    # uses CMP + a direct jump; any other expression is evaluated and compared with 0.
    def condition(self, name: str, false_label: str) -> None:
        self.advance()  # if / while
        self.advance_if(T.LPAREN)
        if self.is_comparison():
            self.emit(f"{JUMP_IF_FALSE[self.compare()]} {false_label}")
        else:
            self.expression()
            self.emit("CMP AX, 0")
            self.emit(f"JE {false_label}")
        self.advance_if(T.RPAREN)
        if not self.current_is(T.LBRACE):
            raise IRError(f"In the {name}, parentheses must surround the entire condition.")

    def if_stmt(self) -> None:
        false_label = self.new_label("IF_FALSE")
        self.condition("if", false_label)
        self.block()
        self.label(false_label)

    def while_stmt(self) -> None:
        start, end = self.new_label("WHILE_START"), self.new_label("WHILE_END")
        self.label(start)
        self.condition("while", end)
        self.block()
        self.emit(f"JMP {start}")
        self.label(end)

    # Load the variable into AX, divide by 10 to get the digits and print them with INT 21H.
    def print_stmt(self) -> None:
        self.advance()  # print
        self.advance()  # (
        name = self.current_token().lexeme
        self.advance()  # ID
        self.advance()  # )
        self.emit(f"MOV AX, {name}")
        self.emit("MOV DL, 10")
        self.emit("DIV DL")
        self.emit("MOV TENS, AL")
        self.emit("MOV ONES, AH")
        for digit in ("TENS", "ONES"):
            self.emit(f"MOV DL, {digit}")
            self.emit("ADD DL, 30H")
            self.emit("MOV AH, 02H")
            self.emit("INT 21H")

    # ---------- expressions ----------

    def expression(self) -> None:  # COMPARISON | SUM
        if self.is_comparison():
            self.emit(f"{SET_IF_TRUE[self.compare()]} AL")
            self.emit("MOV AH, 0")
            return
        self.sum()
        if self.current_token().kind in SET_IF_TRUE:
            raise IRError("In a comparison, both sides must be simple operands.")

    def compare(self) -> T:  # a (== | > | <) b: sets the flags and returns the operator
        self.load_into_ax(self.operand())
        operator = self.current_token().kind
        self.advance()
        right = self.operand()
        self.require_simple("the comparison", FORBIDDEN_AFTER_COMPARISON)
        is_bool = self.symbol_table.get(right) == "bool" or right in ("true", "false")
        right_text = "1" if right == "true" else ("0" if right == "false" else right)
        self.emit(f"CMP {'AL' if is_bool else 'AX'}, {right_text}")
        return operator

    def sum(self) -> None:  # TERM [ ( @ | # ) OPERAND ]*
        self.term()
        while self.current_token().kind in (T.AT, T.HASH):
            mnemonic = "ADD" if self.current_is(T.AT) else "SUB"
            self.advance()
            right = self.operand()
            self.require_simple("the addition or subtraction", FORBIDDEN_AFTER_SUM)
            self.emit(f"{mnemonic} AX, {right}")

    def term(self) -> None:  # OPERAND [ ( & | | ) OPERAND ]*
        self.load_into_ax(self.operand())
        while self.current_token().kind in (T.AMPERSAND, T.PIPE):
            mnemonic = self.current_token().kind
            self.advance()
            self.emit(f"MOV BX, {self.operand()}")
            if mnemonic == T.AMPERSAND:
                self.emit("MUL BX")
            else:
                self.emit("MOV DX, 0")
                self.emit("DIV BX")

    def operand(self) -> str:  # ID | NUM | true | false, as text
        token = self.current_token()
        if token.kind in (T.TRUE, T.FALSE):
            self.advance()
            return token.lexeme
        if token.kind in (T.ID, T.NUM):
            self.advance()
            return token.lexeme
        if token.kind == T.LPAREN:
            raise IRError("Parentheses are not allowed inside an expression.")
        raise IRError("Expected a variable, a number, or true/false.")

    def load_into_ax(self, operand: str) -> None:  # a bool is DB: load into AL and leave AH = 0
        if self.symbol_table.get(operand) == "bool" or operand in ("true", "false"):
            value = "1" if operand == "true" else ("0" if operand == "false" else operand)
            self.emit(f"MOV AL, {value}")
            self.emit("MOV AH, 0")
        else:
            self.emit(f"MOV AX, {operand}")

    def require_simple(self, context: str, forbidden: tuple[T, ...]) -> None:
        if self.current_token().kind in forbidden:
            raise IRError(f"The right-hand side of {context} must be a simple operand.")

    def is_comparison(self) -> bool:  # is it "operand ( == | > | < ) ..."?
        return self.position + 1 < len(self.tokens) and self.tokens[self.position + 1].kind in SET_IF_TRUE

    # ---------- emission ----------

    def emit(self, line: str) -> None:  # "MOV AX, a" -> ("", "MOV", "AX, a")
        operator, _, attribute = line.partition(" ")
        self.rows.append(("", operator, attribute))

    def label(self, name: str) -> None:
        self.rows.append((f"{name}:", "", ""))

    def new_label(self, prefix: str) -> str:
        self.label_number += 1
        return f"{prefix}_{self.label_number}"


def generate_ir(symbol_table: dict[str, str], tokens: list[Token]) -> list[tuple[str, str, str]]:
    has_print = any(token.kind == T.PRINT for token in tokens)
    if not symbol_table and not has_print:
        return []
    rows = list(HEADER)
    for name, data_type in symbol_table.items():
        rows.append((name, "DW" if data_type == "int" else "DB", "?"))
    if has_print:  # where print splits the number into tens and ones
        rows += [("TENS", "DB", "?"), ("ONES", "DB", "?")]
    generator = IRGenerator(tokens, symbol_table)
    generator.block()
    return rows + CODE + generator.rows + FOOTER
