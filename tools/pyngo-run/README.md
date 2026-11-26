# pyngo-run

A small executor for the object code that Pyngo emits. The compiler stays in
Python; this is the "what happens after the last phase" piece, written in Go
with no dependencies outside the standard library.

## Build and run

```bash
uv run pyngo build examples/loop.pyn --json > loop.json   # from the repo root
cd tools/pyngo-run
go run . ../../loop.json
```

The program's output goes to stdout. With `-vars`, the final variables go to
stderr:

```console
$ go run . -vars ../../loop.json
03
i = 3
TENS = 0
ONES = 3
```

| Flag | Meaning |
|---|---|
| `-vars` | print the final variables to stderr |
| `-steps N` | instruction budget (default 200000); stops endless programs |
| `-quiet` | discard the program output |

Exit codes: `0` ok, `1` runtime error (division by zero, bad opcode, step
limit), `2` usage or invalid input.

## Input

`pyngo build --json` (and `POST /object`) return:

```json
{
  "ok": true,
  "data": [{"address": "0000 0000 0000 0000", "content": "0000 0000  0000 0000", "hex": "00 00", "text": "i : int"}],
  "code": [{"address": "0000 0000 0000 0000", "content": "1011 1000  0000 0000  0000 0000", "hex": "B8 00 00", "text": "MOV AX, 0"}],
  "errors": []
}
```

`hex` is concatenated in row order: DATA becomes the data segment, CODE the
code segment, both at offset 0. `ok: false` is a compiler error and is
reported, never executed.

## The machine

Only the instructions the compiler can emit are implemented, with the same
semantics as `tests/differential/emulator.py`:

- `MOV` (`B0`–`BF`, `88`–`8B`, `A1`, `A3`, `C6`, `C7`)
- `ADD` / `SUB` / `CMP` (`01`, `03`, `05`, `29`, `2B`, `2D`, `39`, `3B`,
  `80`, `81`, `83`)
- `MUL` / `DIV` (`F6`, `F7`, groups 4 and 6)
- `PUSH` / `POP`, `CALL` / `RET`, `JMP` / `Jcc`, `INT 21H` (AH=02H), `HLT`
- 64 KB data segment and 64 KB stack segment: `[BP+n]` reads SS, like real
  mode, which is exactly what the `print` routine depends on.

## Tests

```bash
gofmt -l .        # must print nothing
go vet ./...
go test ./...
```

`testdata/loop.json` and `testdata/if.json` are compiled from
`examples/loop.pyn` and `testdata/if.pyn`. The golden test checks the output
and the exact instruction count reported by the Python emulator, so a
different decoding (a wrong displacement, a missing byte) fails the test.

A one-off cross-check of 100 seeded random programs from
`tests/differential/generator.py` produced identical output and final
variables in both implementations.
