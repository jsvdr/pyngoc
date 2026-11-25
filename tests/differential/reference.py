"""Reference model for the differential tests.

A generated program is stored as a small tree. This module renders it to source
text and interprets it with the rules of the language: 16-bit unsigned
integers, int-only operators, unsigned comparisons and a `print` that writes
the two-digit form (00..99).

Nothing here imports the compiler: it is an independent description of what a
program must do, so a wrong byte in the object code shows up as a mismatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

MAX_INT = 0xFFFF
PRINT_LIMIT = 99
STEP_BUDGET = 200_000

SUM_OPERATORS = ("@", "#")
TERM_OPERATORS = ("&", "|")


class ReferenceError(Exception):
    """The program does something the reference model does not define."""


# ---------- expressions ----------


@dataclass(frozen=True)
class Constant:
    value: int


@dataclass(frozen=True)
class Variable:
    name: str


@dataclass(frozen=True)
class Binary:
    operator: str
    left: Expression
    right: Expression


@dataclass(frozen=True)
class Comparison:
    operator: str
    left: Expression
    right: Expression


Expression: TypeAlias = Constant | Variable | Binary | Comparison


# ---------- statements ----------


@dataclass(frozen=True)
class Assignment:
    name: str
    expression: Expression


@dataclass(frozen=True)
class Conditional:
    condition: Expression
    body: tuple[Statement, ...]


@dataclass(frozen=True)
class Loop:
    """`while (counter < limit) { body; counter = counter @ 1; }`."""

    counter: str
    limit: int
    body: tuple[Statement, ...]


@dataclass(frozen=True)
class PrintStatement:
    name: str


Statement: TypeAlias = Assignment | Conditional | Loop | PrintStatement


@dataclass(frozen=True)
class Program:
    int_variables: tuple[tuple[str, int], ...]
    bool_variables: tuple[tuple[str, bool], ...]
    statements: tuple[Statement, ...]


# ---------- rendering ----------
#
# The renderer mirrors the grammar: a comparison may only appear at the top of an
# expression, a SUM holds TERMs and a TERM holds single factors. Because every
# chain is built left-nested, the text needs no parentheses.


def render_expression(node: Expression) -> str:
    if isinstance(node, Comparison):
        return f"{render_sum(node.left)} {node.operator} {render_sum(node.right)}"
    return render_sum(node)


def render_sum(node: Expression) -> str:
    if isinstance(node, Binary) and node.operator in SUM_OPERATORS:
        return f"{render_sum(node.left)} {node.operator} {render_sum(node.right)}"
    return render_term(node)


def render_term(node: Expression) -> str:
    if isinstance(node, Binary) and node.operator in TERM_OPERATORS:
        return f"{render_term(node.left)} {node.operator} {render_term(node.right)}"
    return render_factor(node)


def render_factor(node: Expression) -> str:
    if isinstance(node, Constant):
        return str(node.value)
    if isinstance(node, Variable):
        return node.name
    raise ReferenceError("only a constant or a variable can be a factor")


def render_statement(statement: Statement, depth: int) -> list[str]:
    indent = "    " * depth

    if isinstance(statement, Assignment):
        return [f"{indent}{statement.name} = {render_expression(statement.expression)};"]

    if isinstance(statement, Conditional):
        lines = [f"{indent}if ({render_expression(statement.condition)}) {{"]
        for child in statement.body:
            lines.extend(render_statement(child, depth + 1))
        lines.append(f"{indent}}};")
        return lines

    if isinstance(statement, Loop):
        lines = [f"{indent}while ({statement.counter} < {statement.limit}) {{"]
        for child in statement.body:
            lines.extend(render_statement(child, depth + 1))
        lines.append(f"{indent}}};")
        return lines

    return [f"{indent}print ( {statement.name} );"]


def render_source(program: Program) -> str:
    lines = ["{"]
    for name, value in program.int_variables:
        lines.append(f"    int {name} = {value};")
    for name, value in program.bool_variables:
        lines.append(f"    bool {name} = {'true' if value else 'false'};")
    for statement in program.statements:
        lines.extend(render_statement(statement, 1))
    lines.append("}")
    return "\n".join(lines) + "\n"


# ---------- interpretation ----------


def evaluate(node: Expression, variables: dict[str, int | bool]) -> int | bool:
    if isinstance(node, Constant):
        return node.value

    if isinstance(node, Variable):
        return variables[node.name]

    if isinstance(node, Comparison):
        left = evaluate(node.left, variables)
        right = evaluate(node.right, variables)
        if isinstance(left, bool) != isinstance(right, bool):
            raise ReferenceError("both sides of a comparison must have the same type")
        if node.operator == "==":
            return left == right
        if isinstance(left, bool) or isinstance(right, bool):
            raise ReferenceError("'>' and '<' require int operands")
        if node.operator == ">":
            return left > right
        if node.operator == "<":
            return left < right
        raise ReferenceError(f"unknown comparison '{node.operator}'")

    left = evaluate(node.left, variables)
    right = evaluate(node.right, variables)
    if isinstance(left, bool) or isinstance(right, bool):
        raise ReferenceError(f"operator '{node.operator}' requires int operands")

    if node.operator == "@":
        result = left + right
    elif node.operator == "#":
        result = left - right
    elif node.operator == "&":
        result = left * right
    elif node.operator == "|":
        if right == 0:
            raise ReferenceError("division by zero")
        result = left // right
    else:
        raise ReferenceError(f"unknown operator '{node.operator}'")

    return result & MAX_INT


@dataclass(frozen=True)
class ReferenceResult:
    output: str
    printed: tuple[int, ...]
    variables: dict[str, int | bool]


class Interpreter:
    def __init__(self, program: Program) -> None:
        self.variables: dict[str, int | bool] = {}
        for name, value in program.int_variables:
            self.variables[name] = value
        for name, value in program.bool_variables:
            self.variables[name] = value
        self.statements = program.statements
        self.printed: list[int] = []
        self.steps = 0

    def run(self) -> ReferenceResult:
        self.block(self.statements)
        return ReferenceResult(
            output="".join(f"{value:02d}" for value in self.printed),
            printed=tuple(self.printed),
            variables=dict(self.variables),
        )

    def block(self, statements: tuple[Statement, ...]) -> None:
        for statement in statements:
            self.statement(statement)

    def statement(self, statement: Statement) -> None:
        self.charge()

        if isinstance(statement, Assignment):
            value = evaluate(statement.expression, self.variables)
            if isinstance(self.variables[statement.name], bool) != isinstance(value, bool):
                raise ReferenceError(f"type mismatch in the assignment to '{statement.name}'")
            self.variables[statement.name] = value
            return

        if isinstance(statement, Conditional):
            if evaluate(statement.condition, self.variables):
                self.block(statement.body)
            return

        if isinstance(statement, Loop):
            condition = Comparison("<", Variable(statement.counter), Constant(statement.limit))
            while evaluate(condition, self.variables):
                self.charge()
                self.block(statement.body)
            return

        value = self.variables[statement.name]
        if isinstance(value, bool):
            raise ReferenceError("print only accepts int variables")
        if not 0 <= value <= PRINT_LIMIT:
            raise ReferenceError(f"{value} does not fit in the two-digit routine")
        self.printed.append(value)

    def charge(self) -> None:
        self.steps += 1
        if self.steps > STEP_BUDGET:
            raise ReferenceError("step limit exceeded: the program probably does not terminate")
