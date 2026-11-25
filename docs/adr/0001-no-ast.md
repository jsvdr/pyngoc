# 1. The parser validates, it does not build a tree

- Status: accepted
- Date: 2026-11-10

## Context

The compiler is teaching material: each phase must be readable and
explainable in an exam. The usual design is `source → AST → walks`, but an
AST adds a file of node classes, a visitor (or a chain of `isinstance`
checks), and a second representation of the same grammar.

## Decision

There is no AST. `parser.py` recognizes the grammar and reports errors; it
returns `(bool, list[str])`. `semantic.py`, `ir.py` and `codegen.py` copy the
parser's shape — the same method names, the same order — and walk the token
list again with their own cursor.

## Consequences

- Every phase reads top to bottom and mirrors the production it implements,
  so explaining one method explains one grammar rule.
- The token list is traversed four times. That is irrelevant at this scale
  (programs are a few hundred tokens) and it keeps the code straightforward.
- The three walkers must stay in sync with the grammar. A rule change means
  touching each walker, which is visible in the diff.
- If an optimizer is ever added it will need its own representation; that
  decision is deferred until the optimizer exists.
