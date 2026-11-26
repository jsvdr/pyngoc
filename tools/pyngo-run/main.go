// Command pyngo-run executes the object code produced by `pyngo build --json`.
//
//	pyngo build examples/loop.pyn --json > loop.json
//	pyngo-run loop.json
//
// It is a deliberately small 8086 executor: only the instructions the compiler
// emits, with 64 KB data and stack segments. The Python package stays the
// compiler; this is the "what happens after the last phase" demo in Go.
package main

import (
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr))
}

func run(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("pyngo-run", flag.ContinueOnError)
	flags.SetOutput(stderr)
	showVariables := flags.Bool("vars", false, "print the final variables to stderr")
	steps := flags.Uint64("steps", 200_000, "maximum number of instructions")
	quiet := flags.Bool("quiet", false, "discard the program output")
	_ = flags.Parse(args)

	if flags.NArg() > 1 {
		fmt.Fprintln(stderr, "usage: pyngo-run [-vars] [-steps N] [-quiet] [program.json]")

		return 2
	}

	if *steps == 0 {
		fmt.Fprintln(stderr, "pyngo-run: -steps must be greater than zero")

		return 2
	}

	input, err := readInput(flags.Args(), stdin)
	if err != nil {
		fmt.Fprintf(stderr, "pyngo-run: %v\n", err)

		return 2
	}

	program, err := ParseProgram(input)
	if err != nil {
		fmt.Fprintf(stderr, "pyngo-run: %v\n", err)

		return 2
	}

	machine := NewMachine(program)
	machine.MaxSteps = *steps

	output, err := machine.Run()
	if err != nil {
		fmt.Fprintf(stderr, "pyngo-run: runtime error: %v\n", err)

		return 1
	}

	if !*quiet {
		_, _ = fmt.Fprint(stdout, output)
	}

	if *showVariables {
		// The program prints digits without a trailing newline; keep the
		// variables readable when both streams share a terminal.
		if output != "" && !strings.HasSuffix(output, "\n") {
			_, _ = fmt.Fprintln(stderr)
		}

		printVariables(stderr, program, machine)
	}

	return 0
}

// readInput reads the named file, or stdin when there is no name or it is "-".
func readInput(args []string, stdin io.Reader) ([]byte, error) {
	if len(args) == 1 && args[0] != "-" {
		return os.ReadFile(args[0])
	}

	return io.ReadAll(stdin)
}

func printVariables(w io.Writer, program *Program, machine *Machine) {
	for _, variable := range program.Variables() {
		value := machine.ReadVariable(variable.Address, variable.Wide)
		_, _ = fmt.Fprintf(w, "%s = %d\n", variable.Name, value)
	}
}
