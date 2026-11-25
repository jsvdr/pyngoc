# 5. Object code is checked with a differential test

- Status: accepted
- Date: 2026-11-20

## Context

The object-code phase has two ways of being wrong: a wrong byte (the encoder)
or a wrong sequence of instructions (the generator). Snapshot tests catch both
only for the programs someone thought of, and a wrong snapshot just makes the
test agree with the bug.

## Decision

`tests/test_differential.py` generates 300 programs from a fixed seed, compiles
them, runs the bytes in a small x86-16 emulator
(`tests/differential/emulator.py`) and compares the result with an independent
reference interpreter (`tests/differential/reference.py`):

- the text written through `INT 21H` / `AH=02H`, and
- the final value of every variable in the data segment.

The emulator has separate data and stack segments, like real mode, so a wrong
segment override (`[BP+2]` reading `DS` instead of `SS`) fails the test. The
reference interpreter never imports the compiler: it is a second description
of the language.

The generator only builds programs the pipeline accepts, and discards programs
that would print a value above 99, which the two-digit routine does not
define.

## Consequences

- Two independent implementations must agree on 300 random programs; the
  emulator and the reference can disagree only if a test is wrong.
- A regression in the encoder or the generator fails with the offending
  program printed in the assertion message.
- Three extra files live under `tests/` and the emulator only supports the
  emitted subset; it is a test tool, not a general emulator.
- The seed makes failures reproducible: the same program index fails every
  time until it is fixed.
