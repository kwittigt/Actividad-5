# Variables
ASM=nasm
EMU="C:\Program Files\qemu\qemu-system-i386.exe"
SRC=boot.asm
BIN=boot.bin

all: run

$(BIN): $(SRC)
	$(ASM) -f bin $(SRC) -o $(BIN)

run: $(BIN)
	$(EMU) -drive format=raw,file=$(BIN) -display gtk

clean:
	del /Q $(BIN) 2>nul || true

.PHONY: all run clean