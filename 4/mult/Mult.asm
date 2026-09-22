// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/4/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)
// The algorithm is based on repetitive addition.

@R2
M=0 // Initialize R2 to 0

@R0
D=M // D = R0 (multiplier / counter to count down)

(LOOP)
@END
D;JLE // if the counter D gets to zero loop ends

@R1
D=M // D = R1 (value we add each time through loop)

@R2
M=D+M // R2 = R1 + R2

@R0
M=M-1 // minus 1 to counter
D=M  // Refresh D with the counters new value so loop check at top sees updated count

@LOOP
0;JMP  // Go back and check conditions again at top of loop

(END)
@END
0;JMP 
