package main

import (
	"bytes"
	"os"
	"strings"
	"testing"
)

func loadProgram(t *testing.T, path string) *Program {
	t.Helper()

	input, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}

	program, err := ParseProgram(input)
	if err != nil {
		t.Fatalf("parse %s: %v", path, err)
	}

	return program
}

func runCode(t *testing.T, code []byte) (*Machine, string, error) {
	t.Helper()

	machine := NewMachine(&Program{code: code})
	output, err := machine.Run()

	return machine, output, err
}

func TestGoldenPrograms(t *testing.T) {
	// The step counts come from the Python emulator in tests/differential, so
	// decoding a different number of bytes here would fail this test.
	cases := []struct {
		path   string
		output string
		steps  uint64
	}{
		{"testdata/loop.json", "03", 59},
		{"testdata/if.json", "42", 31},
	}

	for _, testCase := range cases {
		machine := NewMachine(loadProgram(t, testCase.path))

		output, err := machine.Run()
		if err != nil {
			t.Fatalf("%s: %v", testCase.path, err)
		}

		if output != testCase.output {
			t.Errorf("%s: output = %q, want %q", testCase.path, output, testCase.output)
		}

		if machine.steps != testCase.steps {
			t.Errorf("%s: %d steps, want %d", testCase.path, machine.steps, testCase.steps)
		}
	}
}

func TestVariablesComeFromTheDataPanel(t *testing.T) {
	program := loadProgram(t, "testdata/if.json")
	machine := NewMachine(program)

	if _, err := machine.Run(); err != nil {
		t.Fatal(err)
	}

	variables := program.Variables()

	if len(variables) != 3 {
		t.Fatalf("got %d variables, want 3", len(variables))
	}

	if variables[0].Name != "a" || !variables[0].Wide {
		t.Fatalf("first variable = %+v, want a as a word", variables[0])
	}

	if value := machine.ReadVariable(variables[0].Address, variables[0].Wide); value != 42 {
		t.Errorf("a = %d, want 42", value)
	}
}

func TestMOVAndADD(t *testing.T) {
	machine, _, err := runCode(t, []byte{
		0xB8, 0x07, 0x00, // MOV AX, 7
		0x05, 0x23, 0x00, // ADD AX, 35
		0xF4, // HLT
	})
	if err != nil {
		t.Fatal(err)
	}

	if got := machine.get16(ax); got != 42 {
		t.Errorf("AX = %d, want 42", got)
	}
}

func TestComparisonAndConditionalJump(t *testing.T) {
	code := []byte{
		0xB8, 0x05, 0x00, // MOV AX, 5
		0x3D, 0x05, 0x00, // CMP AX, 5
		0x0F, 0x84, 0x03, 0x00, // JE +3: skip the next instruction
		0xB8, 0x00, 0x00, // MOV AX, 0
		0xF4, // HLT
	}

	machine, _, err := runCode(t, code)
	if err != nil {
		t.Fatal(err)
	}

	if got := machine.get16(ax); got != 5 {
		t.Errorf("AX = %d, want 5 (the jump was not taken)", got)
	}

	code[4] = 0x04 // CMP AX, 4: equal is false now

	machine, _, err = runCode(t, code)
	if err != nil {
		t.Fatal(err)
	}

	if got := machine.get16(ax); got != 0 {
		t.Errorf("AX = %d, want 0 (the jump was taken)", got)
	}
}

func TestPushPopRoundTrip(t *testing.T) {
	machine, _, err := runCode(t, []byte{
		0xB8, 0x2A, 0x00, // MOV AX, 42
		0x50, // PUSH AX
		0x58, // POP AX
		0xF4, // HLT
	})
	if err != nil {
		t.Fatal(err)
	}

	if got := machine.get16(sp); got != initialSP {
		t.Errorf("SP = %04X, want %04X", got, initialSP)
	}
}

func TestBPRelativeReadUsesTheStackSegment(t *testing.T) {
	machine, _, err := runCode(t, []byte{
		0xB8, 0x34, 0x12, // MOV AX, 1234H
		0x50,             // PUSH AX: the argument
		0xE8, 0x00, 0x00, // CALL +0: pushes the return address, like the compiler
		0x89, 0xE5, // MOV BP, SP
		0x8B, 0x46, 0x02, // MOV AX, [BP+2]: the argument, not the return address
		0xF4, // HLT
	})
	if err != nil {
		t.Fatal(err)
	}

	if got := machine.get16(ax); got != 0x1234 {
		t.Errorf("AX = %04X, want 1234", got)
	}
}

func TestPrintWithINT21H(t *testing.T) {
	_, output, err := runCode(t, []byte{
		0xB2, 'A', // MOV DL, 'A'
		0xB4, 0x02, // MOV AH, 02H
		0xCD, 0x21, // INT 21H
		0xF4, // HLT
	})
	if err != nil {
		t.Fatal(err)
	}

	if output != "A" {
		t.Errorf("output = %q, want %q", output, "A")
	}
}

func TestStepLimit(t *testing.T) {
	_, _, err := runCode(t, []byte{0xE9, 0xFD, 0xFF}) // JMP to itself

	if err == nil || !strings.Contains(err.Error(), "step limit") {
		t.Fatalf("err = %v, want a step limit error", err)
	}
}

func TestDivisionByZero(t *testing.T) {
	_, _, err := runCode(t, []byte{0xF7, 0xF3}) // DIV BX, BX = 0

	if err == nil || !strings.Contains(err.Error(), "division by zero") {
		t.Fatalf("err = %v, want a division by zero error", err)
	}
}

func TestUnsupportedOpcode(t *testing.T) {
	_, _, err := runCode(t, []byte{0xCC}) // INT3 is not emitted

	if err == nil || !strings.Contains(err.Error(), "unsupported opcode CC") {
		t.Fatalf("err = %v, want an unsupported opcode error", err)
	}
}

func TestParseRejectsCompilerErrors(t *testing.T) {
	_, err := ParseProgram([]byte(`{"ok": false, "errors": ["Line 1: TYPE ERROR: boom"]}`))

	if err == nil || !strings.Contains(err.Error(), "Line 1: TYPE ERROR: boom") {
		t.Fatalf("err = %v, want the compiler message", err)
	}
}

func TestParseRejectsInvalidHex(t *testing.T) {
	_, err := ParseProgram([]byte(`{"ok": true, "data": [], "code": [{"hex": "ZZ"}]}`))

	if err == nil || !strings.Contains(err.Error(), "invalid hex") {
		t.Fatalf("err = %v, want an invalid hex error", err)
	}
}

func TestParseAcceptsCompactHex(t *testing.T) {
	program, err := ParseProgram([]byte(`{"ok": true, "data": [], "code": [{"hex": "B80700"}]}`))
	if err != nil {
		t.Fatal(err)
	}

	if len(program.code) != 3 {
		t.Errorf("decoded %d bytes, want 3", len(program.code))
	}
}

func TestRunReadsAFile(t *testing.T) {
	var stdout, stderr bytes.Buffer

	if code := run([]string{"testdata/loop.json"}, strings.NewReader(""), &stdout, &stderr); code != 0 {
		t.Fatalf("exit = %d, stderr = %s", code, stderr.String())
	}

	if stdout.String() != "03" {
		t.Errorf("stdout = %q, want %q", stdout.String(), "03")
	}
}

func TestRunPrintsVariablesToStderr(t *testing.T) {
	var stdout, stderr bytes.Buffer

	if code := run([]string{"-vars", "testdata/if.json"}, strings.NewReader(""), &stdout, &stderr); code != 0 {
		t.Fatalf("exit = %d, stderr = %s", code, stderr.String())
	}

	if stdout.String() != "42" {
		t.Errorf("stdout = %q, want %q", stdout.String(), "42")
	}

	if !strings.Contains(stderr.String(), "a = 42") {
		t.Errorf("stderr = %q, want it to contain %q", stderr.String(), "a = 42")
	}

	if !strings.HasPrefix(stderr.String(), "\n") {
		t.Errorf("stderr = %q, want a newline before the variables", stderr.String())
	}
}

func TestRunQuietDiscardsTheOutput(t *testing.T) {
	var stdout, stderr bytes.Buffer

	if code := run([]string{"-quiet", "testdata/loop.json"}, strings.NewReader(""), &stdout, &stderr); code != 0 {
		t.Fatalf("exit = %d, stderr = %s", code, stderr.String())
	}

	if stdout.String() != "" {
		t.Errorf("stdout = %q, want nothing", stdout.String())
	}
}

func TestRunRejectsAMissingFile(t *testing.T) {
	var stdout, stderr bytes.Buffer

	if code := run([]string{"nope.json"}, strings.NewReader(""), &stdout, &stderr); code != 2 {
		t.Errorf("exit = %d, want 2", code)
	}
}

func TestRunRejectsZeroSteps(t *testing.T) {
	var stdout, stderr bytes.Buffer

	if code := run([]string{"-steps", "0", "testdata/loop.json"}, strings.NewReader(""), &stdout, &stderr); code != 2 {
		t.Errorf("exit = %d, want 2", code)
	}
}
