package main

import (
	"fmt"
	"strings"
)

// Register numbers follow the x86 encoding, not the names: AX CX DX BX SP BP SI DI.
const (
	ax = iota
	cx
	dx
	bx
	sp
	bp
	si
	di
)

const (
	memorySize = 65536
	initialSP  = 0xFFFE
)

// operand is a decoded ModR/M operand: a register, or memory at an address.
type operand struct {
	isMemory bool
	stack    bool // BP-relative reads and writes use SS, like real mode
	address  int
	register int
}

func register(index int) operand {
	return operand{register: index}
}

func memory(address int, stack bool) operand {
	return operand{isMemory: true, stack: stack, address: address & 0xFFFF}
}

type flags struct {
	carry    bool
	zero     bool
	sign     bool
	overflow bool
}

// Machine is the 8086 subset the compiler emits. Data and stack are separate
// 64 KB segments, as in the real mode model the IR describes.
type Machine struct {
	registers [8]uint16
	flags     flags
	data      [memorySize]byte
	stack     [memorySize]byte
	code      []byte
	ip        int
	halted    bool
	steps     uint64
	output    strings.Builder
	err       error

	// MaxSteps stops a program that never reaches HLT.
	MaxSteps uint64
}

// NewMachine copies the DATA segment and starts with an empty stack.
func NewMachine(program *Program) *Machine {
	machine := &Machine{code: program.code, MaxSteps: 200_000}
	copy(machine.data[:], program.data)
	machine.registers[sp] = initialSP

	return machine
}

// Run executes until HLT or the first error.
func (m *Machine) Run() (string, error) {
	for !m.halted && m.err == nil {
		m.step()
	}

	if m.err != nil {
		return "", m.err
	}

	return m.output.String(), nil
}

// ReadVariable reads a variable once the program has halted.
func (m *Machine) ReadVariable(address int, wide bool) uint16 {
	return m.read(memory(address, false), wide)
}

// ---------- registers and memory ----------

func (m *Machine) get16(index int) uint16 {
	return m.registers[index]
}

func (m *Machine) set16(index int, value uint16) {
	m.registers[index] = value
}

// 8-bit registers 0..3 are the low halves (AL CL DL BL) and 4..7 the high ones.
func (m *Machine) get8(index int) byte {
	base := index & 3
	if index < 4 {
		return byte(m.registers[base])
	}

	return byte(m.registers[base] >> 8)
}

func (m *Machine) set8(index int, value byte) {
	base := index & 3
	if index < 4 {
		m.registers[base] = m.registers[base]&0xFF00 | uint16(value)

		return
	}

	m.registers[base] = m.registers[base]&0x00FF | uint16(value)<<8
}

func (m *Machine) read(op operand, wide bool) uint16 {
	if !op.isMemory {
		if wide {
			return m.get16(op.register)
		}

		return uint16(m.get8(op.register))
	}

	segment := m.data[:]
	if op.stack {
		segment = m.stack[:]
	}

	if wide {
		return uint16(segment[op.address]) | uint16(segment[(op.address+1)&0xFFFF])<<8
	}

	return uint16(segment[op.address])
}

func (m *Machine) write(op operand, value uint16, wide bool) {
	if !op.isMemory {
		if wide {
			m.set16(op.register, value)
		} else {
			m.set8(op.register, byte(value))
		}

		return
	}

	segment := m.data[:]
	if op.stack {
		segment = m.stack[:]
	}

	segment[op.address] = byte(value)
	if wide {
		segment[(op.address+1)&0xFFFF] = byte(value >> 8)
	}
}

func (m *Machine) push16(value uint16) {
	m.registers[sp] -= 2
	m.write(memory(int(m.registers[sp]), true), value, true)
}

func (m *Machine) pop16() uint16 {
	value := m.read(memory(int(m.registers[sp]), true), true)
	m.registers[sp] += 2

	return value
}

// ---------- instruction stream ----------

func (m *Machine) fail(format string, args ...any) {
	if m.err == nil {
		m.err = fmt.Errorf(format, args...)
	}
}

func (m *Machine) fetch8() byte {
	if m.err != nil {
		return 0
	}

	if m.ip < 0 || m.ip >= len(m.code) {
		m.fail("the instruction pointer left the code segment at %04X", m.ip)

		return 0
	}

	value := m.code[m.ip]
	m.ip++

	return value
}

func (m *Machine) fetch16() uint16 {
	low := m.fetch8()
	high := m.fetch8()

	return uint16(low) | uint16(high)<<8
}

func (m *Machine) fetchSigned8() int {
	return int(int8(m.fetch8()))
}

func (m *Machine) fetchSigned16() int {
	return int(int16(m.fetch16()))
}

// memoryBase maps r/m 100..111 to the register the address comes from and
// whether that segment is SS (BP) or DS (the rest).
func memoryBase(rm int) (int, bool) {
	switch rm {
	case 6:
		return bp, true
	case 4:
		return si, false
	case 5:
		return di, false
	default:
		return bx, false
	}
}

func (m *Machine) decodeModRM() (int, operand) {
	modrm := m.fetch8()
	mod := int(modrm >> 6)
	reg := int(modrm >> 3 & 7)
	rm := int(modrm & 7)

	if mod == 3 {
		return reg, register(rm)
	}

	if mod == 0 && rm == 6 { // [disp16]: no base register
		return reg, memory(int(m.fetch16()), false)
	}

	base, stack := memoryBase(rm)
	address := int(m.get16(base))
	displacement := 0

	switch mod {
	case 1:
		displacement = m.fetchSigned8()
	case 2:
		displacement = m.fetchSigned16()
	}

	return reg, memory(address+displacement, stack)
}

// ---------- flags and ALU ----------

func (m *Machine) setFlags(result uint16, carry, overflow, wide bool) {
	signBit := uint16(0x8000)
	if !wide {
		signBit = 0x80
	}

	m.flags.carry = carry
	m.flags.zero = result == 0
	m.flags.sign = result&signBit != 0
	m.flags.overflow = overflow
}

func (m *Machine) applyALU(operation string, destination operand, source uint16, wide bool) {
	mask := uint16(0xFFFF)
	signBit := uint16(0x8000)
	if !wide {
		mask = 0xFF
		signBit = 0x80
	}

	left := m.read(destination, wide)
	store := true
	carry := false
	overflow := false
	var result uint16

	if operation == "ADD" {
		sum := uint32(left) + uint32(source)
		result = uint16(sum) & mask
		carry = sum > uint32(mask)
		overflow = ^(left^source)&(left^result)&signBit != 0
	} else { // SUB or CMP: CMP only sets the flags
		result = (left - source) & mask
		carry = left < source
		overflow = (left^source)&(left^result)&signBit != 0
		store = operation == "SUB"
	}

	m.setFlags(result, carry, overflow, wide)

	if store {
		m.write(destination, result, wide)
	}
}

func (m *Machine) jumpTaken(condition byte) bool {
	switch condition {
	case 0x82: // JB
		return m.flags.carry
	case 0x83: // JAE
		return !m.flags.carry
	case 0x84: // JE
		return m.flags.zero
	case 0x85: // JNE
		return !m.flags.zero
	case 0x86: // JBE
		return m.flags.carry || m.flags.zero
	case 0x87: // JA
		return !m.flags.carry && !m.flags.zero
	}

	m.fail("unsupported jump condition 0F %02X", condition)

	return false
}

// ---------- execution ----------

func (m *Machine) step() {
	m.steps++
	if m.steps > m.MaxSteps {
		m.fail("step limit exceeded: the program probably does not terminate")

		return
	}

	opcode := m.fetch8()

	switch {
	case opcode >= 0xB0 && opcode <= 0xB7: // MOV r8, imm8
		m.set8(int(opcode-0xB0), m.fetch8())
	case opcode >= 0xB8 && opcode <= 0xBF: // MOV r16, imm16
		m.set16(int(opcode-0xB8), m.fetch16())
	case opcode == 0xA1: // MOV AX, [disp16]
		m.set16(ax, m.read(memory(int(m.fetch16()), false), true))
	case opcode == 0xA3: // MOV [disp16], AX
		m.write(memory(int(m.fetch16()), false), m.get16(ax), true)
	case opcode == 0x88 || opcode == 0x89: // MOV r/m, reg
		wide := opcode == 0x89
		reg, destination := m.decodeModRM()
		m.write(destination, m.read(register(reg), wide), wide)
	case opcode == 0x8A || opcode == 0x8B: // MOV reg, r/m
		wide := opcode == 0x8B
		reg, source := m.decodeModRM()
		m.write(register(reg), m.read(source, wide), wide)
	case opcode == 0xC6 || opcode == 0xC7: // MOV r/m, imm
		wide := opcode == 0xC7
		_, destination := m.decodeModRM()

		var immediate uint16
		if wide {
			immediate = m.fetch16()
		} else {
			immediate = uint16(m.fetch8())
		}

		m.write(destination, immediate, wide)
	case opcode == 0x01 || opcode == 0x03 || opcode == 0x29 || opcode == 0x2B || opcode == 0x39 || opcode == 0x3B:
		operation := map[byte]string{0x01: "ADD", 0x03: "ADD", 0x29: "SUB", 0x2B: "SUB", 0x39: "CMP", 0x3B: "CMP"}[opcode]
		reg, rm := m.decodeModRM()

		if opcode == 0x01 || opcode == 0x29 || opcode == 0x39 { // r/m, reg
			m.applyALU(operation, rm, m.get16(reg), true)
		} else { // reg, r/m
			m.applyALU(operation, register(reg), m.read(rm, true), true)
		}
	case opcode == 0x05 || opcode == 0x2D || opcode == 0x3D: // ALU AX, imm16
		operation := map[byte]string{0x05: "ADD", 0x2D: "SUB", 0x3D: "CMP"}[opcode]
		m.applyALU(operation, register(ax), m.fetch16(), true)
	case opcode == 0x80 || opcode == 0x81 || opcode == 0x83: // group 1: ALU r/m, imm
		wide := opcode != 0x80
		group, destination := m.decodeModRM()

		var immediate uint16
		switch opcode {
		case 0x83:
			immediate = uint16(int16(int8(m.fetch8()))) // sign-extended byte
		case 0x81:
			immediate = m.fetch16()
		default:
			immediate = uint16(m.fetch8())
		}

		operation := map[int]string{0: "ADD", 5: "SUB", 7: "CMP"}[group]
		if operation == "" {
			m.fail("unsupported group 1 operation /%d", group)

			return
		}

		m.applyALU(operation, destination, immediate, wide)
	case opcode == 0xF6 || opcode == 0xF7: // group 3: MUL / DIV
		wide := opcode == 0xF7
		group, source := m.decodeModRM()
		value := m.read(source, wide)

		switch group {
		case 4:
			m.multiply(value, wide)
		case 6:
			m.divide(value, wide)
		default:
			m.fail("unsupported group 3 operation /%d", group)
		}
	case opcode >= 0x50 && opcode <= 0x57: // PUSH reg
		m.push16(m.get16(int(opcode - 0x50)))
	case opcode >= 0x58 && opcode <= 0x5F: // POP reg
		m.set16(int(opcode-0x58), m.pop16())
	case opcode == 0xE8: // CALL rel16
		relative := m.fetchSigned16()
		m.push16(uint16(m.ip))
		m.ip = (m.ip + relative) & 0xFFFF
	case opcode == 0xE9: // JMP rel16
		relative := m.fetchSigned16()
		m.ip = (m.ip + relative) & 0xFFFF
	case opcode == 0x0F: // Jcc rel16
		condition := m.fetch8()
		relative := m.fetchSigned16()

		if m.jumpTaken(condition) {
			m.ip = (m.ip + relative) & 0xFFFF
		}
	case opcode == 0xCD: // INT imm8
		interrupt := m.fetch8()

		if interrupt == 0x21 && m.get8(4) == 0x02 { // AH=02H: print DL
			m.output.WriteByte(m.get8(dx))
		} else {
			m.fail("unsupported interrupt INT %02X", interrupt)
		}
	case opcode == 0xF4: // HLT
		m.halted = true
	case opcode == 0xC3: // RET
		m.ip = int(m.pop16())
	case opcode == 0x90: // NOP
	default:
		m.fail("unsupported opcode %02X at IP %04X", opcode, m.ip-1)
	}
}

func (m *Machine) multiply(source uint16, wide bool) {
	if wide {
		result := uint32(m.get16(ax)) * uint32(source)
		m.set16(dx, uint16(result>>16))
		m.set16(ax, uint16(result))
		m.flags.carry = result>>16 != 0
		m.flags.zero = result == 0
	} else {
		result := uint16(m.get8(ax)) * source
		m.set16(ax, result)
		m.flags.carry = result > 0xFF
		m.flags.zero = result == 0
	}

	m.flags.overflow = m.flags.carry
	m.flags.sign = false
}

func (m *Machine) divide(source uint16, wide bool) {
	if source == 0 {
		m.fail("division by zero")

		return
	}

	if wide {
		dividend := uint32(m.get16(dx))<<16 | uint32(m.get16(ax))
		quotient := dividend / uint32(source)
		if quotient > 0xFFFF {
			m.fail("DIV overflow")

			return
		}

		m.set16(ax, uint16(quotient))
		m.set16(dx, uint16(dividend%uint32(source)))

		return
	}

	dividend := uint16(m.get16(ax))
	quotient := uint16(dividend / source)
	if quotient > 0xFF {
		m.fail("DIV overflow")

		return
	}

	m.set8(ax, byte(quotient))
	m.set8(4, byte(dividend%source)) // AH
}
