# 2. Every expression is computed in `AX`

- Status: accepted
- Date: 2026-11-10

## Context

Expressions need somewhere to live while they are evaluated. A real compiler
allocates registers or spills to the stack; both need a register allocator and
a stack frame layout, which is a lot of machinery for a teaching compiler.

## Decision

One accumulator: `AX`. A statement loads its left operand into `AX`, applies
each operator to `AX`, and stores the result. When an operator needs the
left-hand value alive while the right-hand side is evaluated (a mixed
precedence such as `a @ b & c`, or a division), `codegen.py` pushes `AX`,
computes the right side, moves it to `BX`, pops the old value and combines the
two.

The IR generator is deliberately simpler: it only accepts *simple* operands on
the right-hand side and reports `IRError` instead of generating code it cannot
express. The object-code generator is the one that handles the general case.

## Consequences

- The generated code is easy to read and to verify by hand: `MOV`, one
  operator, `MOV`.
- `MUL`/`DIV` use `BX` as the second operand and `DX` is cleared before a
  16-bit division, so the flags and the high half are predictable.
- With a single accumulator, deeply nested expressions need the stack; the IR
  panel documents that as a limitation instead of hiding it
  ([`limitations.md`](../limitations.md)).
- No register allocation means no optimization: `i = i @ 1` always reloads
  `i` from memory.
