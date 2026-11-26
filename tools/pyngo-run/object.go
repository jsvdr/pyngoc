// Package main implements pyngo-run: a small executor for the object code that
// `pyngo build --json` emits. It reads the same JSON the web UI receives, so
// the compiler stays in Python and only the machine is written in Go.
package main

import (
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
)

// Row mirrors one line of the DATA or CODE panel.
type Row struct {
	Address string `json:"address"`
	Content string `json:"content"`
	Hex     string `json:"hex"`
	Text    string `json:"text"`
}

// document is the JSON written by `pyngo build --json` and by POST /object.
type document struct {
	OK     bool     `json:"ok"`
	Data   []Row    `json:"data"`
	Code   []Row    `json:"code"`
	Errors []string `json:"errors"`
}

// Program is the decoded object code: bytes plus the rows they came from.
type Program struct {
	Data []Row
	Code []Row

	data []byte
	code []byte
}

// Variable is one name from the DATA panel and where it lives in the segment.
type Variable struct {
	Name    string
	Address int
	Wide    bool
}

// ParseProgram validates the JSON before anything runs. A document with
// ok=false is a compiler error, not something to execute.
func ParseProgram(input []byte) (*Program, error) {
	var doc document
	if err := json.Unmarshal(input, &doc); err != nil {
		return nil, fmt.Errorf("not a pyngo object file: %w", err)
	}

	if !doc.OK {
		if len(doc.Errors) > 0 {
			return nil, fmt.Errorf("the compiler rejected the program: %s", strings.Join(doc.Errors, "; "))
		}

		return nil, errors.New("the object file is not ok")
	}

	data, err := decodeRows(doc.Data)
	if err != nil {
		return nil, fmt.Errorf("DATA panel: %w", err)
	}

	code, err := decodeRows(doc.Code)
	if err != nil {
		return nil, fmt.Errorf("CODE panel: %w", err)
	}

	if len(code) == 0 {
		return nil, errors.New("the CODE panel is empty")
	}

	return &Program{Data: doc.Data, Code: doc.Code, data: data, code: code}, nil
}

// decodeRows concatenates the hex field of every row, in order.
func decodeRows(rows []Row) ([]byte, error) {
	var out []byte

	for index, row := range rows {
		// "B8 07 00" and "B80700" mean the same thing.
		raw := strings.Join(strings.Fields(row.Hex), "")

		payload, err := hex.DecodeString(raw)
		if err != nil {
			return nil, fmt.Errorf("row %d has an invalid hex field: %w", index, err)
		}

		out = append(out, payload...)
	}

	return out, nil
}

// Variables reads the names and widths out of the DATA rows. The compiler lays
// them out in order, so the offset is the sum of the previous row sizes.
func (p *Program) Variables() []Variable {
	address := 0
	variables := make([]Variable, 0, len(p.Data))

	for _, row := range p.Data {
		size := len(strings.Fields(row.Hex))
		name := strings.TrimSpace(strings.SplitN(row.Text, ":", 2)[0])

		variables = append(variables, Variable{Name: name, Address: address, Wide: size >= 2})
		address += size
	}

	return variables
}
