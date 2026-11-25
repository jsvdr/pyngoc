# Object code: tokens + symbol table -> 16-bit x86 bytes. Every expression leaves its result in AX.
from collections.abc import Callable
from typing import NamedTuple, TypeAlias, TypedDict

from .cursor import TokenCursor
from .encoder import EncoderError, Operand, encode, encode_jump
from .tokens import Token
from .tokens import TokenKind as T

DATA_BASE = 0x0000  # DATA and CODE are different segments: both start at 0
CODE_BASE = 0x0000

AX: Operand = ("reg", "AX")
BX: Operand = ("reg", "BX")
BP: Operand = ("reg", "BP")
DX: Operand = ("reg", "DX")
SP: Operand = ("reg", "SP")
AL: Operand = ("reg", "AL")
AH: Operand = ("reg", "AH")
DL: Operand = ("reg", "DL")
COMPARISONS = {T.EQ: "JE", T.GREATER: "JA", T.LESS: "JB"}  # unsigned: values 0..65535
ARITHMETIC = (T.AT, T.HASH, T.AMPERSAND, T.PIPE)


class Label(NamedTuple):
    name: str


class Instruction(NamedTuple):
    mnemonic: str
    operands: tuple[Operand, ...]
    force: str | None
    text: str


class Jump(NamedTuple):
    mnemonic: str
    label: str


ObjectItem: TypeAlias = Label | Instruction | Jump


class Row(TypedDict):
    address: int
    bytes: list[int]
    text: str


class PanelRow(TypedDict):
    address: str
    content: str
    hex: str
    text: str


class CodegenError(Exception):
    """Something that this phase cannot generate."""


def imm(value: int) -> Operand:
    return ("imm", value)


def mem(address: int) -> Operand:
    return ("mem", address)


def operand_text(operand: Operand) -> str:
    if operand[0] == "reg":
        return str(operand[1])
    if operand[0] == "imm":
        return str(operand[1])
    if len(operand) == 2:
        return f"[{int(operand[1]):04X}h]"
    return f"[{operand[1]}{int(operand[2]):+d}]"


class CodeGenerator(TokenCursor):
    def __init__(self, tokens: list[Token], symbol_table: dict[str, str]) -> None:
        super().__init__(tokens)
        self.symbol_table = symbol_table
        self.addresses: dict[str, int] = {}
        address = DATA_BASE
        for name, data_type in symbol_table.items():  # int: 2 bytes · bool: 1 byte
            self.addresses[name] = address
            address += 1 if data_type == "bool" else 2
        self.has_print = any(token.kind == T.PRINT for token in tokens)
        if self.has_print:  # TENS and ONES: 1 byte each, after the variables
            self.addresses["TENS"], self.addresses["ONES"] = address, address + 1
        self.items: list[ObjectItem] = []
        self.label_number = 0

    def generate(self) -> list[tuple[int, list[int], str]]:
        self.block()
        self.emit("HLT")
        if self.has_print:
            self.print_routine()
        return assemble(self.items)

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
        name = self.current_token()
        self.advance()  # ID
        self.advance()  # =
        self.expression()
        register = AL if self.symbol_table.get(name.lexeme) == "bool" else AX  # bool = 1 byte
        self.emit("MOV", mem(self.address_of(name)), register)

    def condition(self, false_label: str) -> None:  # jump if the expression is 0
        self.advance()  # if / while
        self.expression()
        self.emit("CMP", AX, imm(0))
        self.jump("JE", false_label)

    def if_stmt(self) -> None:
        false_label = self.new_label("IF_FALSE")
        self.condition(false_label)
        self.block()
        self.label(false_label)

    def while_stmt(self) -> None:
        start, end = self.new_label("WHILE_START"), self.new_label("WHILE_END")
        self.label(start)
        self.condition(end)
        self.block()
        self.jump("JMP", start)
        self.label(end)

    def print_stmt(self) -> None:
        self.advance()  # print
        self.advance()  # (
        name = self.current_token()
        self.advance()  # ID
        self.advance()  # )
        self.emit("MOV", AX, mem(self.address_of(name)))
        self.emit("PUSH", AX)
        self.jump("CALL", "print_routine")
        self.emit("ADD", SP, imm(2), force="imm8")

    def print_routine(self) -> None:  # same as IR: DIV DL, TENS, ONES, INT 21H
        tens, ones = self.addresses["TENS"], self.addresses["ONES"]
        self.label("print_routine")
        # BP-relative addressing reads SS, where PUSH stored the argument.
        self.emit("MOV", BP, SP)
        self.emit("MOV", AX, ("mem", "BP", 2))
        self.emit("MOV", DL, imm(10))
        self.emit("DIV", DL)
        self.emit("MOV", mem(tens), AL, text="MOV TENS, AL")
        self.emit("MOV", mem(ones), AH, text="MOV ONES, AH")
        for address, name in ((tens, "TENS"), (ones, "ONES")):
            self.emit("MOV", DL, mem(address), text=f"MOV DL, {name}")
            self.emit("ADD", DL, imm(0x30), text="ADD DL, 30H")
            self.emit("MOV", AH, imm(2), text="MOV AH, 02H")
            self.emit("INT", imm(0x21), text="INT 21H")
        self.emit("RET")

    # ---------- expressions ----------

    def expression(self) -> None:  # SUM [ (== | > | <) SUM ]: leaves 0 or 1 in AX
        self.sum()
        kind = self.current_token().kind
        if kind in COMPARISONS:
            self.advance()
            self.operate("CMP", self.sum)
            true_label, end_label = self.new_label("CMP_TRUE"), self.new_label("CMP_END")
            self.jump(COMPARISONS[kind], true_label)
            self.emit("MOV", AX, imm(0))
            self.jump("JMP", end_label)
            self.label(true_label)
            self.emit("MOV", AX, imm(1))
            self.label(end_label)

    def sum(self) -> None:
        self.binary({T.AT: "ADD", T.HASH: "SUB"}, self.term)

    def term(self) -> None:
        self.binary({T.AMPERSAND: "MUL", T.PIPE: "DIV"}, self.factor)

    def binary(self, operators: dict[T, str], next_operand: Callable[[], None]) -> None:
        next_operand()
        while self.current_token().kind in operators:
            mnemonic = operators[self.current_token().kind]
            self.advance()
            self.operate(mnemonic, next_operand)

    def operate(self, mnemonic: str, right: Callable[[], None]) -> None:
        """AX = AX <mnemonic> right-hand side. MUL and DIV work with BX."""
        simple, mul_div = self.is_simple(), mnemonic in ("MUL", "DIV")
        if simple and not mul_div:
            self.emit(mnemonic, AX, self.source())  # ADD AX,[x] · SUB AX,1 · CMP AX,5
            return
        if simple:
            self.emit("MOV", BX, self.source())
        else:  # compound right-hand side (or bool): AX waits on the stack
            self.emit("PUSH", AX)
            right()
            self.emit("MOV", BX, AX)
            self.emit("POP", AX)
        if mnemonic == "DIV":
            self.emit("MOV", DX, imm(0))
        if mul_div:
            self.emit(mnemonic, BX)
        else:
            self.emit(mnemonic, AX, BX)

    def factor(self) -> None:  # ID | NUM | BOOL | ( EXPRESSION )
        if self.current_is(T.LPAREN):
            self.advance()
            self.expression()
            self.advance()
            return
        token = self.current_token()
        if token.kind in (T.TRUE, T.FALSE):
            self.emit("MOV", AL, self.source())
            self.emit("MOV", AH, imm(0))
        elif self.symbol_table.get(token.lexeme) == "bool":  # 1 byte: load AL and clear AH
            self.emit("MOV", AL, mem(self.address_of(token)))
            self.emit("MOV", AH, imm(0))
            self.advance()
        else:
            self.emit("MOV", AX, self.source())

    def is_simple(self) -> bool:  # a single int ID / NUM, with no operator after it
        token = self.current_token()
        return (
            token.kind in (T.ID, T.NUM)
            and self.symbol_table.get(token.lexeme) != "bool"
            and self.position + 1 < len(self.tokens)
            and self.tokens[self.position + 1].kind not in ARITHMETIC
        )

    def source(self) -> Operand:  # ID -> [address] · NUM -> number · true / false -> 1 / 0
        token = self.current_token()
        self.advance()
        if token.kind == T.ID:
            return mem(self.address_of(token))
        return imm(int(token.lexeme) if token.kind == T.NUM else int(token.kind == T.TRUE))

    def address_of(self, token: Token) -> int:
        if token.lexeme not in self.addresses:
            raise CodegenError(
                f"Line {token.line}: OBJECT CODE ERROR: Variable '{token.lexeme}' has not been declared."
            )
        return self.addresses[token.lexeme]

    # ---------- emission ----------

    def emit(self, mnemonic: str, *operands: Operand, force: str | None = None, text: str = "") -> None:
        parts = ", ".join(operand_text(operand) for operand in operands)
        self.items.append(Instruction(mnemonic, operands, force, text or f"{mnemonic} {parts}".strip()))

    def jump(self, mnemonic: str, label: str) -> None:
        self.items.append(Jump(mnemonic, label))

    def label(self, name: str) -> None:
        self.items.append(Label(name))

    def new_label(self, prefix: str) -> str:
        self.label_number += 1
        return f"{prefix}_{self.label_number}"


def assemble(items: list[ObjectItem]) -> list[tuple[int, list[int], str]]:
    """Two passes: the first computes addresses; the second already knows jump targets."""
    destinations: dict[str, int] = {}
    rows: list[tuple[int, list[int], str]] = []
    for _ in range(2):
        rows = []
        position = CODE_BASE
        for item in items:
            if isinstance(item, Label):
                destinations[item.name] = position
                continue
            if isinstance(item, Jump):
                code = encode_jump(item.mnemonic, destinations.get(item.label, 0), position)
                text = f"{item.mnemonic} {item.label}"
            else:
                code, text = encode(item.mnemonic, item.operands, item.force), item.text
            rows.append((position, code, text))
            position += len(code)
    return rows


def format_address(address: int) -> str:
    return " ".join(f"{(address >> shift) & 0xF:04b}" for shift in (12, 8, 4, 0))


def format_binary(code: list[int]) -> str:
    return "  ".join(f"{byte >> 4:04b} {byte & 0xF:04b}" for byte in code)


def format_hex(code: list[int]) -> str:
    return " ".join(f"{byte:02X}" for byte in code)


def panel_row(address: int, code: list[int], text: str) -> PanelRow:
    """One panel row: ADDRESS and CONTENT in nibbles (4 bits), HEX in bytes."""
    return {
        "address": format_address(address),
        "content": format_binary(code),
        "hex": format_hex(code),
        "text": text,
    }


def generate_object_code(
    tokens: list[Token], symbol_table: dict[str, str]
) -> tuple[bool, list[PanelRow], list[PanelRow], list[str]]:
    generator = CodeGenerator(tokens, symbol_table)
    try:
        rows = generator.generate()
    except (CodegenError, EncoderError) as error:
        return False, [], [], [str(error)]
    data = [  # int takes 2 bytes; bool, TENS and ONES take 1
        panel_row(
            address,
            [0] * (2 if symbol_table.get(name) == "int" else 1),
            f"{name} : {symbol_table.get(name, 'byte')}",
        )
        for name, address in generator.addresses.items()
    ]
    return True, data, [panel_row(*row) for row in rows], ["Object code OK"]
