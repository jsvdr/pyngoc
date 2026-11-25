"""Random program generator for the differential tests.

It only builds programs the whole pipeline accepts: declared variables, int-only
arithmetic, comparisons in conditions, loops that always advance a counter, and
`print` of an int variable. Programs that print a value above 99 are discarded
because the emitted two-digit routine only defines 00..99.
"""

from __future__ import annotations

import random

from .reference import (
    PRINT_LIMIT,
    Assignment,
    Binary,
    Comparison,
    Conditional,
    Constant,
    Expression,
    Interpreter,
    Loop,
    PrintStatement,
    Program,
    ReferenceError,
    Statement,
    Variable,
)

INT_VARIABLES = ("a", "b", "c")
BOOL_VARIABLES = ("p", "q")
COMPARISONS = ("==", ">", "<")


class ProgramGenerator:
    def __init__(self, random_source: random.Random) -> None:
        self.random = random_source
        self.int_names = list(INT_VARIABLES[: self.random.randint(2, 3)])
        self.bool_names = list(BOOL_VARIABLES[: self.random.randint(1, 2)])
        self.counters: list[tuple[str, int]] = []

    # ---------- program ----------

    def program(self) -> Program:
        statements = self.block(depth=0, count=self.random.randint(3, 6))

        int_variables = [(name, self.random.randint(0, 9)) for name in self.int_names]
        int_variables += self.counters
        bool_variables = [(name, self.random.random() < 0.5) for name in self.bool_names]

        return Program(tuple(int_variables), tuple(bool_variables), tuple(statements))

    def block(self, depth: int, count: int) -> list[Statement]:
        return [self.statement(depth) for _ in range(count)]

    def statement(self, depth: int) -> Statement:
        if depth >= 2:
            return self.simple_statement()

        roll = self.random.random()
        if roll < 0.50:
            return self.simple_statement()
        if roll < 0.70:
            return self.conditional(depth)
        if roll < 0.85:
            return self.loop(depth)
        return PrintStatement(self.random.choice(self.int_names))

    def simple_statement(self) -> Statement:
        if self.random.random() < 0.75:
            return Assignment(self.random.choice(self.int_names), self.sum())
        return Assignment(self.random.choice(self.bool_names), self.condition())

    def conditional(self, depth: int) -> Statement:
        body = tuple(self.block(depth + 1, self.random.randint(0, 2)))
        return Conditional(self.condition(), body)

    def loop(self, depth: int) -> Statement:
        counter = f"i{len(self.counters) + 1}"
        self.counters.append((counter, 0))

        body = self.block(depth + 1, self.random.randint(0, 2))
        body.append(Assignment(counter, Binary("@", Variable(counter), Constant(1))))

        return Loop(counter, self.random.randint(1, 4), tuple(body))

    # ---------- expressions ----------

    def condition(self) -> Expression:
        if self.random.random() < 0.30:
            return Variable(self.random.choice(self.bool_names))
        return Comparison(self.random.choice(COMPARISONS), self.sum(), self.sum())

    def sum(self) -> Expression:
        node: Expression = self.term()
        for _ in range(self.random.randint(0, 2)):
            node = Binary(self.random.choice(("@", "#")), node, self.term())
        return node

    def term(self) -> Expression:
        node: Expression = self.factor()
        for _ in range(self.random.randint(0, 2)):
            operator = self.random.choice(("&", "|"))
            if operator == "|":
                # A constant divisor keeps the program free of division by zero.
                node = Binary(operator, node, Constant(self.random.randint(1, 9)))
            else:
                node = Binary(operator, node, self.factor())
        return node

    def factor(self) -> Expression:
        if self.random.random() < 0.50:
            return Constant(self.random.randint(0, 9))
        return Variable(self.random.choice(self.int_names))


def generate_programs(count: int, seed: int) -> list[Program]:
    """Generate `count` programs that the reference model accepts."""
    random_source = random.Random(seed)
    programs: list[Program] = []
    attempts = 0

    while len(programs) < count and attempts < count * 10:
        attempts += 1
        program = ProgramGenerator(random_source).program()

        try:
            result = Interpreter(program).run()
        except ReferenceError:
            continue

        if any(value > PRINT_LIMIT for value in result.printed):
            continue

        programs.append(program)

    if len(programs) < count:
        raise ReferenceError(f"could not generate {count} valid programs (got {len(programs)})")

    return programs
