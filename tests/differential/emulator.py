"""A tiny 16-bit x86 emulator for the subset emitted by codegen.py.

It is not a general x86 emulator. It interprets exactly the instructions the
compiler emits: MOV, ADD/SUB/CMP, MUL/DIV, Jcc/JMP/CALL/RET, PUSH/POP, INT 21h
and HLT. Data and stack are separate 64 KB arrays, so a BP-relative read must
use SS just like real mode.
"""

from dataclasses import dataclass
from typing import Literal

from pyngo.codegen import PanelRow

REG16 = ("AX", "CX", "DX", "BX", "SP", "BP", "SI", "DI")
REG8 = ("AL", "CL", "DL", "BL", "AH", "CH", "DH", "BH")
MEMORY_BASE = {7: "BX", 6: "BP", 4: "SI", 5: "DI"}
REG_INDEX = {name: index for index, name in enumerate(REG16)}
REG8_INDEX = {name: index for index, name in enumerate(REG8)}


class EmulatorError(Exception):
    """The program used an instruction or state the emulator cannot handle."""


@dataclass
class Flags:
    carry: bool = False
    zero: bool = False
    sign: bool = False
    overflow: bool = False


# An operand is either ("reg", index) or ("mem", segment, address).
Operand = tuple[Literal["reg"], int] | tuple[Literal["mem"], str, int]


class Emulator:
    def __init__(self, data: list[PanelRow], code: list[PanelRow]) -> None:
        self.data = bytearray(65536)
        self.stack = bytearray(65536)
        self.code = bytearray()
        self.regs = [0] * 8
        self.regs[REG_INDEX["SP"]] = 0xFFFE
        self.flags = Flags()
        self.ip = 0
        self.halted = False
        self.output: list[str] = []
        self.steps = 0
        self.max_steps = 200_000

        position = 0
        for row in data:
            payload = bytes.fromhex(row["hex"])
            self.data[position : position + len(payload)] = payload
            position += len(payload)

        for row in code:
            self.code.extend(bytes.fromhex(row["hex"]))

    def run(self) -> str:
        while not self.halted:
            self.step()
        return "".join(self.output)

    def read_variable(self, address: int, wide: bool) -> int:
        """Read a variable from the data segment once the program has halted."""
        return self.read_operand(("mem", "data", address), wide)

    # ---------- registers and memory ----------

    def get16(self, index: int) -> int:
        return self.regs[index]

    def set16(self, index: int, value: int) -> None:
        self.regs[index] = value & 0xFFFF

    def get8(self, index: int) -> int:
        base = index & 3
        if index < 4:
            return self.regs[base] & 0xFF
        return (self.regs[base] >> 8) & 0xFF

    def set8(self, index: int, value: int) -> None:
        base = index & 3
        value &= 0xFF
        if index < 4:
            self.regs[base] = (self.regs[base] & 0xFF00) | value
        else:
            self.regs[base] = (self.regs[base] & 0x00FF) | (value << 8)

    def read_operand(self, operand: Operand, wide: bool) -> int:
        if operand[0] == "reg":
            index = int(operand[1])
            return self.get16(index) if wide else self.get8(index)

        segment, address = str(operand[1]), int(operand[2])
        memory = self.data if segment == "data" else self.stack
        if wide:
            return memory[address] | (memory[(address + 1) & 0xFFFF] << 8)
        return memory[address]

    def write_operand(self, operand: Operand, value: int, wide: bool) -> None:
        if operand[0] == "reg":
            index = int(operand[1])
            if wide:
                self.set16(index, value)
            else:
                self.set8(index, value)
            return

        segment, address = str(operand[1]), int(operand[2])
        memory = self.data if segment == "data" else self.stack
        if wide:
            memory[address] = value & 0xFF
            memory[(address + 1) & 0xFFFF] = (value >> 8) & 0xFF
        else:
            memory[address] = value & 0xFF

    def push16(self, value: int) -> None:
        self.regs[REG_INDEX["SP"]] = (self.regs[REG_INDEX["SP"]] - 2) & 0xFFFF
        self.write_operand(("mem", "stack", self.regs[REG_INDEX["SP"]]), value, True)

    def pop16(self) -> int:
        value = self.read_operand(("mem", "stack", self.regs[REG_INDEX["SP"]]), True)
        self.regs[REG_INDEX["SP"]] = (self.regs[REG_INDEX["SP"]] + 2) & 0xFFFF
        return value

    # ---------- instruction stream ----------

    def fetch8(self) -> int:
        if self.ip >= len(self.code):
            raise EmulatorError("The instruction pointer left the code segment.")
        value = self.code[self.ip]
        self.ip += 1
        return value

    def fetch16(self) -> int:
        low = self.fetch8()
        high = self.fetch8()
        return low | (high << 8)

    def fetch_s8(self) -> int:
        value = self.fetch8()
        return value - 256 if value & 0x80 else value

    def fetch_s16(self) -> int:
        value = self.fetch16()
        return value - 65536 if value & 0x8000 else value

    def decode_modrm(self, wide: bool) -> tuple[int, Operand]:
        modrm = self.fetch8()
        mod, reg, rm = modrm >> 6, (modrm >> 3) & 7, modrm & 7

        if mod == 3:
            return reg, ("reg", rm)

        if mod == 0 and rm == 6:
            return reg, ("mem", "data", self.fetch16())

        base_name = MEMORY_BASE[rm]
        segment = "stack" if base_name == "BP" else "data"
        base = self.get16(REG_INDEX[base_name])

        displacement = 0
        if mod == 1:
            displacement = self.fetch_s8()
        elif mod == 2:
            displacement = self.fetch_s16()

        return reg, ("mem", segment, (base + displacement) & 0xFFFF)

    # ---------- flags and ALU ----------

    def set_flags(self, result: int, carry: bool, wide: bool, overflow: bool) -> None:
        mask = 0x8000 if wide else 0x80
        self.flags.carry = carry
        self.flags.zero = result == 0
        self.flags.sign = bool(result & mask)
        self.flags.overflow = overflow

    def apply_alu(self, operation: str, destination: Operand, source: int, wide: bool) -> None:
        mask = 0xFFFF if wide else 0xFF
        left = self.read_operand(destination, wide)
        if operation == "ADD":
            raw = left + source
            result = raw & mask
            carry = raw > mask
            sign_bit = 0x8000 if wide else 0x80
            overflow = bool((~(left ^ source) & (left ^ result)) & sign_bit)
            store = True
        else:  # SUB or CMP
            result = (left - source) & mask
            carry = left < source
            sign_bit = 0x8000 if wide else 0x80
            overflow = bool(((left ^ source) & (left ^ result)) & sign_bit)
            store = operation == "SUB"

        self.set_flags(result, carry, wide, overflow)
        if store:
            self.write_operand(destination, result, wide)

    def jump_taken(self, condition: int) -> bool:
        if condition == 0x82:
            return self.flags.carry
        if condition == 0x83:
            return not self.flags.carry
        if condition == 0x84:
            return self.flags.zero
        if condition == 0x85:
            return not self.flags.zero
        if condition == 0x86:
            return self.flags.carry or self.flags.zero
        if condition == 0x87:
            return not self.flags.carry and not self.flags.zero
        raise EmulatorError(f"Unsupported jump condition 0F {condition:02X}.")

    # ---------- execution ----------

    def step(self) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise EmulatorError("Step limit exceeded: the program probably does not terminate.")

        opcode = self.fetch8()

        if 0xB0 <= opcode <= 0xB7:  # MOV r8, imm8
            self.set8(opcode - 0xB0, self.fetch8())
            return

        if 0xB8 <= opcode <= 0xBF:  # MOV r16, imm16
            self.set16(opcode - 0xB8, self.fetch16())
            return

        if opcode == 0xA1:  # MOV AX, [disp16]
            self.set16(0, self.read_operand(("mem", "data", self.fetch16()), True))
            return

        if opcode == 0xA3:  # MOV [disp16], AX
            self.write_operand(("mem", "data", self.fetch16()), self.get16(0), True)
            return

        if opcode in (0x88, 0x89):  # MOV r/m, reg
            wide = opcode == 0x89
            reg, destination = self.decode_modrm(wide)
            self.write_operand(destination, self.read_operand(("reg", reg), wide), wide)
            return

        if opcode in (0x8A, 0x8B):  # MOV reg, r/m
            wide = opcode == 0x8B
            reg, source = self.decode_modrm(wide)
            self.write_operand(("reg", reg), self.read_operand(source, wide), wide)
            return

        if opcode in (0xC6, 0xC7):  # MOV r/m, imm
            wide = opcode == 0xC7
            _, destination = self.decode_modrm(wide)
            immediate = self.fetch16() if wide else self.fetch8()
            self.write_operand(destination, immediate, wide)
            return

        if opcode in (0x01, 0x03, 0x29, 0x2B, 0x39, 0x3B):
            operation = {0x01: "ADD", 0x03: "ADD", 0x29: "SUB", 0x2B: "SUB", 0x39: "CMP", 0x3B: "CMP"}[opcode]
            reg, rm = self.decode_modrm(True)
            if opcode in (0x01, 0x29, 0x39):  # r/m, reg
                self.apply_alu(operation, rm, self.get16(reg), True)
            else:  # reg, r/m
                self.apply_alu(operation, ("reg", reg), self.read_operand(rm, True), True)
            return

        if opcode in (0x05, 0x0D, 0x2D, 0x3D):
            operation = {0x05: "ADD", 0x0D: "SUB", 0x2D: "SUB", 0x3D: "CMP"}[opcode]
            # 0x0D is OR in real x86 and is not emitted; keep the table explicit.
            self.apply_alu(operation, ("reg", 0), self.fetch16(), True)
            return

        if opcode in (0x80, 0x81, 0x83):
            wide = opcode != 0x80
            group, destination = self.decode_modrm(wide)
            if opcode == 0x83:
                immediate = self.fetch_s8()
            elif wide:
                immediate = self.fetch16()
            else:
                immediate = self.fetch8()
            operation = {0: "ADD", 5: "SUB", 7: "CMP"}[group]
            self.apply_alu(operation, destination, immediate, wide)
            return

        if opcode in (0xF6, 0xF7):
            wide = opcode == 0xF7
            group, operand = self.decode_modrm(wide)
            source = self.read_operand(operand, wide)
            if group == 4:
                self.multiply(source, wide)
            elif group == 6:
                self.divide(source, wide)
            else:
                raise EmulatorError(f"Unsupported F6/F7 group {group}.")
            return

        if 0x50 <= opcode <= 0x57:  # PUSH reg
            self.push16(self.get16(opcode - 0x50))
            return

        if 0x58 <= opcode <= 0x5F:  # POP reg
            self.set16(opcode - 0x58, self.pop16())
            return

        if opcode == 0xE8:  # CALL rel16
            relative = self.fetch_s16()
            self.push16(self.ip)
            self.ip = (self.ip + relative) & 0xFFFF
            return

        if opcode == 0xE9:  # JMP rel16
            relative = self.fetch_s16()
            self.ip = (self.ip + relative) & 0xFFFF
            return

        if opcode == 0x0F:
            condition = self.fetch8()
            relative = self.fetch_s16()
            if self.jump_taken(condition):
                self.ip = (self.ip + relative) & 0xFFFF
            return

        if opcode == 0xCD:  # INT imm8
            interrupt = self.fetch8()
            if interrupt == 0x21 and self.get8(REG8_INDEX["AH"]) == 0x02:
                self.output.append(chr(self.get8(REG8_INDEX["DL"])))
                return
            raise EmulatorError(f"Unsupported interrupt INT {interrupt:02X}.")

        if opcode == 0xF4:  # HLT
            self.halted = True
            return

        if opcode == 0xC3:  # RET
            self.ip = self.pop16()
            return

        if opcode == 0x90:  # NOP
            return

        raise EmulatorError(f"Unsupported opcode {opcode:02X} at IP {self.ip - 1:04X}.")

    def multiply(self, source: int, wide: bool) -> None:
        ax, dx = REG_INDEX["AX"], REG_INDEX["DX"]
        if wide:
            result = self.get16(ax) * source
            self.set16(dx, result >> 16)
            self.set16(ax, result)
            self.flags.carry = (result >> 16) != 0
        else:
            result = self.get8(REG8_INDEX["AL"]) * source
            self.set16(ax, result)
            self.flags.carry = (result >> 8) != 0
        self.flags.overflow = self.flags.carry
        self.flags.zero = result == 0
        self.flags.sign = False

    def divide(self, source: int, wide: bool) -> None:
        if source == 0:
            raise EmulatorError("Division by zero.")
        ax, dx = REG_INDEX["AX"], REG_INDEX["DX"]
        if wide:
            dividend = (self.get16(dx) << 16) | self.get16(ax)
            quotient, remainder = divmod(dividend, source)
            if quotient > 0xFFFF:
                raise EmulatorError("DIV overflow.")
            self.set16(ax, quotient)
            self.set16(dx, remainder)
        else:
            dividend = self.get16(ax)
            quotient, remainder = divmod(dividend, source)
            if quotient > 0xFF:
                raise EmulatorError("DIV overflow.")
            self.set8(REG8_INDEX["AL"], quotient)
            self.set8(REG8_INDEX["AH"], remainder)
