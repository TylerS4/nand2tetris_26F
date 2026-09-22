// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/4/Fill.asm

// Runs an infinite loop that listens to the keyboard input. 
// When a key is pressed (any key), the program blackens the screen,
// writes "black" in every pixel when no key is pressed, 
// the screen should be cleared at the end


(LOOP)
    @KBD
    D=M        // Read RAM[24576]  0 if no key, non-zero if key pressed

    @SETWHITE
    D;JEQ      // If D == 0 (no key pressed), fill white
    D=-1       // Key pressed: set D = -1 
    @SETCOLOR
    0;JMP      // Skip white setup and jump directly to save the black color

(SETWHITE)
    D=0        // No key pressed: set D = 0 

(SETCOLOR)
    @color
    M=D        // Store the selected fill pattern 0 or -1 into the variable color

    @SCREEN
    D=A        // Load base address 16384 into D
    @address
    M=D        // Initialize address to 16384

(FILL)
    @color
    D=M        // Get current fill color pattern 0 or -1 from color into D
    @address
    A=M        // Set A to the memory address stored in address variable
    M=D        // Write color value into RAM

    @address
    M=M+1      // Move pointer to next 16-pixel screen memory word
    D=M        // Load updated memory address into D
    @KBD
    D=D-A      // (address - 24576) KBD address is end of screen memory
    @FILL
    D;JNE      // If address != 24576, screen is not fully drawn, repeat

    @LOOP
    0;JMP      // Screen fill completed, loop back to check keyboard