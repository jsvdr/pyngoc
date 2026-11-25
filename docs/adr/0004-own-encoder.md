# 4. The encoder is written here, not delegated to an assembler

- Status: accepted
- Date: 2026-11-15

## Context

Producing bytes for `MOV AX, 5` can be delegated to `nasm`/`yasm` in a
subprocess, or implemented directly. The object-code panel shows
`ADDRESS | CONTENT | HEX` per instruction, which means the compiler must know
each instruction's length, its bytes, and its position anyway.

## Decision

`encoder.py` encodes the instruction subset the compiler emits, using tables:

- `MOV` (`88`/`89`/`8A`/`8B`/`A1`/`A3`/`B0`-`BF`/`C6`/`C7`),
- `ADD`/`SUB`/`CMP` (`01`/`03`/`05`/`0D`… `80`/`81`/`83`),
- `MUL`/`DIV` (`F6`/`F7` with a `/digit`),
- `PUSH`/`POP`, `INT`, `RET`, `HLT`,
- near `JMP` (`E9`), near `CALL` (`E8`) and near `Jcc` (`0F 8x`).

The ModR/M byte is composed from `mod`, `reg` and `r/m`, and a displacement is
picked as 0, 8 or 16 bits depending on its value. Jumps are always near, so
their size is known before the target address is.

## Consequences

- No external assembler, no subprocess, no extra dependency, and the GUI can
  show the exact byte of every instruction.
- The instruction set is fixed: anything outside the tables raises
  `EncoderError`, which is a clear error instead of wrong bytes.
- Every table entry is covered by a unit test in `tests/test_encoder.py`
  (hex and nibbles), and the whole pipeline is covered by the differential
  test.
- Adding an instruction means touching three places (table, encoder branch,
  emulator); that is the cost of owning the encoding.
