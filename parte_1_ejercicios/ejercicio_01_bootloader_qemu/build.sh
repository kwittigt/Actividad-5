#!/bin/bash

# build.sh - Script de compilación y ejecución para bootloader QEMU
# Uso: ./build.sh [compile|run|clean|all]

NASM_CMD="nasm"
QEMU_CMD="qemu-system-i386"
SRC_FILE="boot.asm"
BIN_FILE="boot.bin"

# Colores para terminal
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función de compilación
compile() {
    echo -e "${YELLOW}Compilando $SRC_FILE...${NC}"
    
    if ! command -v $NASM_CMD &> /dev/null; then
        echo -e "${RED}Error: NASM no encontrado. Instala NASM primero.${NC}"
        exit 1
    fi
    
    $NASM_CMD -f bin "$SRC_FILE" -o "$BIN_FILE"
    
    if [ -f "$BIN_FILE" ]; then
        SIZE=$(stat -f%z "$BIN_FILE" 2>/dev/null || stat -c%s "$BIN_FILE" 2>/dev/null)
        echo -e "${GREEN}✓ Compilación exitosa: $BIN_FILE ($SIZE bytes)${NC}"
        
        # Verificar firma de arranque
        if [ $SIZE -eq 512 ]; then
            echo -e "${GREEN}✓ Tamaño correcto: 512 bytes${NC}"
        fi
    else
        echo -e "${RED}✗ Error: No se generó $BIN_FILE${NC}"
        exit 1
    fi
}

# Función de ejecución
run() {
    if [ ! -f "$BIN_FILE" ]; then
        echo -e "${RED}Error: $BIN_FILE no existe. Compila primero.${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Ejecutando QEMU...${NC}"
    
    if ! command -v $QEMU_CMD &> /dev/null; then
        echo -e "${RED}Error: QEMU no encontrado. Instala QEMU primero.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Se abrirá una ventana de QEMU. Usa Ctrl+Alt+G para liberar ratón.${NC}"
    $QEMU_CMD -drive format=raw,file="$BIN_FILE" -display gtk
}

# Función de limpieza
clean() {
    echo -e "${YELLOW}Limpiando archivos...${NC}"
    rm -f "$BIN_FILE"
    echo -e "${GREEN}✓ Limpieza completada${NC}"
}

# Main
case "${1:-all}" in
    compile)
        compile
        ;;
    run)
        run
        ;;
    clean)
        clean
        ;;
    all)
        compile
        run
        ;;
    *)
        echo "Uso: $0 {compile|run|clean|all}"
        echo ""
        echo "  compile  - Compila boot.asm a boot.bin"
        echo "  run      - Ejecuta boot.bin en QEMU"
        echo "  clean    - Elimina boot.bin"
        echo "  all      - Compila y ejecuta (default)"
        exit 1
        ;;
esac

exit 0
