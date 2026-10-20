"""
Hack Assembler (Nand2Tetris Project 6)
Translates a Hack assembly file (.asm) into Hack machine code (.hack).
Usage: python HackAssembler.py Prog.asm   ->  writes Prog.hack
"""
import sys


class Parser:
    """Reads a .asm file and breaks each instruction into its fields."""

    def __init__(self, path):
        # Load the whole file up front as a list of clean instructions
        self.lines = []
        with open(path) as f:
            for raw in f:
                # Drop comments, then remove ALL whitespace (Hack allows "D = M")
                line = raw.split("//")[0]
                line = "".join(line.split())
                # Skip lines that were blank or comment-only
                if line:
                    self.lines.append(line)
        # Start "before" the first line; advance() moves to index 0
        self.index = -1
        self.current = None

    def hasMoreLines(self):
        # True if there is at least one more instruction to read
        return self.index + 1 < len(self.lines)

    def advance(self):
        # Move to the next instruction and make it the current one
        self.index += 1
        self.current = self.lines[self.index]

    def reset(self):
        # Rewind so the second pass can re-read the file
        self.index = -1
        self.current = None

    def instructionType(self):
        # @xxx is an A-instruction, (xxx) is a label, anything else is a C-instruction
        if self.current.startswith("@"):
            return "A_INSTRUCTION"
        if self.current.startswith("("):
            return "L_INSTRUCTION"
        return "C_INSTRUCTION"

    def symbol(self):
        # "@xxx" -> "xxx", "(xxx)" -> "xxx"
        if self.instructionType() == "A_INSTRUCTION":
            return self.current[1:]   # drop the '@'
        return self.current[1:-1]     # drop the '(' and ')'

    # C-instruction format is dest=comp;jump, where dest and jump are optional

    def dest(self):
        # Text before '=' (empty string if there is no '=')
        return self.current.split("=")[0] if "=" in self.current else ""

    def comp(self):
        # Strip off "dest=" and ";jump" to leave just comp
        c = self.current.split("=")[-1]   # everything after '=' (or whole line)
        return c.split(";")[0]            # everything before ';' (or whole string)

    def jump(self):
        # Text after ';' (empty string if there is no ';')
        return self.current.split(";")[1] if ";" in self.current else ""


class Code:
    """Translates C-instruction mnemonics into binary fields."""

    # dest bits are d1 d2 d3 = A, D, M (which registers get the result)
    DEST = {"": "000", 
            "M": "001", 
            "D": "010", 
            "DM": "011", 
            "MD": "011",
            "A": "100", 
            "AM": "101", 
            "MA": "101", 
            "AD": "110", 
            "DA": "110",
            "ADM": "111", 
            "AMD": "111"}

    # jump bits are j1 j2 j3 = jump if out < 0, = 0, > 0
    JUMP = {"": "000", 
            "JGT": "001", 
            "JEQ": "010", 
            "JGE": "011",
            "JLT": "100", 
            "JNE": "101", 
            "JLE": "110", 
            "JMP": "111"}

    # Key = comp mnemonic, value = a-bit + c1..c6 (7 bits total)
    # a-bit = 0 uses the A register, a-bit = 1 uses M (RAM[A]) instead
    # c1..c6 are the ALU control bits zx, nx, zy, ny, f, no
    COMP = {
        "0":   "0101010", 
        "1":   "0111111", 
        "-1":  "0111010",
        "D":   "0001100", 
        "A":   "0110000", 
        "M":   "1110000",
        "!D":  "0001101", 
        "!A":  "0110001", 
        "!M":  "1110001",
        "-D":  "0001111", 
        "-A":  "0110011", 
        "-M":  "1110011",
        "D+1": "0011111", 
        "A+1": "0110111", 
        "M+1": "1110111",
        "D-1": "0001110", 
        "A-1": "0110010", 
        "M-1": "1110010",
        "D+A": "0000010", 
        "D+M": "1000010",
        "D-A": "0010011", 
        "D-M": "1010011",
        "A-D": "0000111", 
        "M-D": "1000111",
        "D&A": "0000000", 
        "D&M": "1000000",
        "D|A": "0010101", 
        "D|M": "1010101",
    }

    # Each method looks the mnemonic up in its table

    @staticmethod
    def dest(m):
        return Code.DEST[m]   # 3 bits

    @staticmethod
    def comp(m):
        return Code.COMP[m]   # 7 bits

    @staticmethod
    def jump(m):
        return Code.JUMP[m]   # 3 bits


class SymbolTable:
    """Maps symbol names to addresses. Starts with Hack's predefined symbols."""

    def __init__(self):
        # Predefined symbols: VM pointers and memory-mapped I/O
        self.table = {"SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
                      "SCREEN": 16384, "KBD": 24576}
        # R0..R15 are just names for RAM[0]..RAM[15]
        for i in range(16):
            self.table["R" + str(i)] = i

    def addEntry(self, symbol, address):
        # Add a new label or variable
        self.table[symbol] = address

    def contains(self, symbol):
        # Has this symbol already been defined?
        return symbol in self.table

    def getAddress(self, symbol):
        # Look up the address bound to a symbol
        return self.table[symbol]


def assemble(inPath):
    parser = Parser(inPath)
    symbols = SymbolTable()

    # First pass: record each label's ROM address (labels take no ROM space)
    # romAddr counts real instructions, so a label points at the next one
    romAddr = 0
    while parser.hasMoreLines():
        parser.advance()
        if parser.instructionType() == "L_INSTRUCTION":
            symbols.addEntry(parser.symbol(), romAddr)
        else:
            romAddr += 1

    # Second pass: translate every A/C instruction to 16-bit binary
    # All labels are known now, so any unknown @name must be a variable
    parser.reset()
    nextVar = 16  # new variables get RAM[16], RAM[17], ...
    outLines = []
    while parser.hasMoreLines():
        parser.advance()
        kind = parser.instructionType()

        if kind == "A_INSTRUCTION":
            sym = parser.symbol()
            if sym.isdigit():
                # @123 -> use the number directly
                value = int(sym)
            elif symbols.contains(sym):
                # Predefined symbol, label, or variable seen earlier
                value = symbols.getAddress(sym)
            else:
                # First time seeing this name -> allocate it as a variable
                symbols.addEntry(sym, nextVar)
                value = nextVar
                nextVar += 1
            outLines.append(format(value, "016b"))  # 0 + 15-bit value

        elif kind == "C_INSTRUCTION":
            # 111 prefix + comp(7) + dest(3) + jump(3) = 16 bits
            bits = ("111" + Code.comp(parser.comp())
                    + Code.dest(parser.dest()) + Code.jump(parser.jump()))
            outLines.append(bits)
        # L_INSTRUCTIONs produce no output

    # Write Prog.hack next to Prog.asm, one 16-bit instruction per line
    outPath = inPath.rsplit(".", 1)[0] + ".hack"
    with open(outPath, "w") as f:
        f.write("\n".join(outLines))
    print("Wrote " + outPath)


if __name__ == "__main__":
    # Expect exactly one argument: the .asm file to assemble
    if len(sys.argv) != 2:
        print("Usage: python HackAssembler.py Prog.asm")
        sys.exit(1)
    assemble(sys.argv[1])