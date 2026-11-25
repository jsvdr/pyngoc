# 3. `int` is an unsigned 16-bit value

- Status: accepted
- Date: 2026-11-15

## Context

The target is 16-bit x86 real mode, where `int` could be signed (two's
complement, `-32768..32767`) or unsigned (`0..65535`). The language only uses
integers for counters, accumulation and printing, and the printer splits a
number into decimal digits by dividing by 10.

## Decision

`int` is an unsigned 16-bit value, `0..65535`. The semantic analyzer rejects
literals above `65535`. Every comparison uses the unsigned condition codes:

| Operator | Jump if false | Jump if true |
|---|---|---|
| `==` | `JNE` | `JE` |
| `>` | `JBE` | `JA` |
| `<` | `JAE` | `JB` |

`MUL` and `DIV` are the unsigned forms (`F7 /4`, `F7 /6`), which is the same
choice.

## Consequences

- `40000 > 5` is true, as a reader of an unsigned language expects. With
  `JG` it would be false, because `40000` has the sign bit set.
- There is no negative literal and no unary minus: subtraction below zero
  wraps around to a large positive number (`0 # 1` is `65535`).
- A division of a number that does not fit in the quotient produces a
  `DIV` overflow at run time; the generator does not prove it away.
- Signed arithmetic would need a different set of jumps, a different `MUL`,
  and a decision about how to print negatives. That is out of scope.
