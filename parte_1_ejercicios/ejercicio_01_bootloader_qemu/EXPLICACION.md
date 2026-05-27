# Ejercicio 1: Mini Sistema Operativo Booteable en Ensamblador

## Descripción General

Este proyecto implementa un bootloader mínimo escrito en ensamblador x86 (modo real) que se ejecuta en QEMU. El programa muestra una pantalla institucional con información del curso, grupo y conceptos fundamentales de arquitectura de computadores.

---

## Proceso de Arranque (Boot Process)

### 1. **Ciclo de Arranque del BIOS**

Cuando la máquina enciende:
1. El **BIOS** (firmware) realiza pruebas de hardware (POST)
2. Lee el **primer sector** de la unidad de almacenamiento (sector 0)
3. Busca la **firma de arranque** `0x55AA` en los últimos 2 bytes (offsets 510-511)
4. Si encuentra la firma, el BIOS carga el bootloader en memoria en la dirección **0x7C00**
5. Salta a `0x7C00` y comienza la ejecución del bootloader

### 2. **Dirección de Carga: 0x7C00**

- **0x7C00** es una dirección convencional estándar en computadores x86
- Equivale a **31744** bytes desde el inicio de la memoria (en modo real)
- Se debe respetar para evitar conflictos con estructuras de BIOS e interrupciones
- En nuestro código: `[ORG 0x7C00]` indica al ensamblador que genere referencias con esta base

### 3. **Firma de Arranque: 0x55AA**

```asm
times 510-($-$$) db 0   ; Rellena con ceros hasta byte 510
dw 0xAA55               ; Firma en Little Endian (se lee como 0x55AA en memoria)
```

- **Posición obligatoria**: bytes 510-511 (últimos 2 bytes del sector de 512 bytes)
- **Valor especial**: `0x55AA` = marca de sector booteable válido
- **Endianness**: En arquitectura x86 (Little Endian), `0xAA55` se almacena como `55 AA` en memoria
- **Función**: El BIOS busca exactamente este patrón para verificar que el sector es booteable

---

## Diferencias: Bootloader vs Sistema Operativo Completo

### Bootloader (Este Proyecto)
✓ Código simple y lineal  
✓ Ejecuta tareas iniciales (inicializar pantalla, mostrar datos)  
✓ Sin gestión de procesos  
✓ Sin multitarea  
✓ Sin protección de memoria  
✓ Sin sistema de archivos  
✓ Sin abstracción de hardware  
✓ **512 bytes máximo** (limitación sector de arranque)  

### Sistema Operativo Real (Linux, Windows, macOS)
✓ Miles de líneas de código  
✓ **Kernel** que administra procesos y memoria  
✓ **Gestor de interrupciones** avanzado  
✓ **Multitarea** preemptiva  
✓ **Protección de memoria** (modos usuario/kernel)  
✓ **Sistema de archivos** (NTFS, ext4, APFS)  
✓ **Drivers** para hardware diverso  
✓ **Shell/GUI** para interacción de usuario  
✓ **APIs** para desarrollo de aplicaciones  

---

## Relación: Firmware → Bootloader → Sistema Operativo

```
┌─────────────────────────────────┐
│    BIOS/UEFI (Firmware)         │
│  - Inicializa hardware          │
│  - Busca sector booteable       │
│  - Carga bootloader en 0x7C00   │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│    Bootloader (512 bytes)       │
│  - Inicializa segmentos         │
│  - Limpia pantalla              │
│  - Escribe en memoria VGA       │
│  - Carga/salta a SO (opcional)  │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  Sistema Operativo Kernel       │
│  - Modo protegido               │
│  - Gestión de memoria           │
│  - Multitarea                   │
│  - Drivers y APIs               │
└─────────────────────────────────┘
```

---

## Componentes Clave en Este Bootloader

### 1. **Inicialización de Segmentos (Modo Real)**

```asm
cli             ; Deshabilitar interrupciones (seguridad)
xor ax, ax      ; AX = 0
mov ds, ax      ; DS (Data Segment) = 0
mov es, ax      ; ES (Extra Segment) = 0  
mov ss, ax      ; SS (Stack Segment) = 0
mov sp, 0x7C00  ; Stack pointer antes del bootloader (crece hacia abajo)
sti             ; Habilitar interrupciones
```

**Por qué?**
- En modo real, la memoria se accede usando: `(Segment << 4) + Offset`
- Establecer segmentos en 0 simplifica direccionamiento
- El stack debe estar en memoria libre, no donde el bootloader está

### 2. **Limpieza de Pantalla con BIOS Int 0x10**

```asm
mov ah, 0x00    ; Función 0x00: Set Video Mode
mov al, 0x03    ; Modo 3: 80x25 texto, 16 colores
int 0x10        ; Interrupción de video del BIOS
```

- **BIOS Interrupt 0x10** = servicios de video
- **Modo 3**: Modo de texto estándar (80 columnas × 25 filas)
- Limpia pantalla y posiciona cursor en (0,0)

### 3. **Escritura Directa en Memoria VGA**

```asm
mov ax, 0xB800  ; Dirección base del buffer de texto VGA
mov es, ax      ; Guardar en Extra Segment para direccionamiento indirecto
```

**Buffer de Video:**
- **0xB8000** = dirección física del buffer de texto VGA
- Cada carácter ocupa **2 bytes**: `[carácter (AL)] [color (AH)]`
- Color: bits 7-4 = fondo, bits 3-0 = frente
  - `0x0B` = Cyan claro sobre fondo negro
  - `0x0A` = Verde claro sobre fondo negro
  - `0x0E` = Amarillo sobre fondo negro
  - `0x0F` = Blanco sobre fondo negro

- **Posicionamiento en pantalla**:
  - Fila 2, Columna 25: `offset = (2 × 80 + 25) × 2 = 160 × 2 + 25 × 2 bytes`
  - Cada fila = 160 bytes (80 caracteres × 2 bytes)

### 4. **Rutina de Impresión**

```asm
print_str:
    push di         ; Guardar posición
.loop:
    lodsb           ; Carga byte de [DS:SI] en AL, SI++
    or al, al       ; ¿Es cero (fin de string)?
    jz .done
    mov [es:di], ax ; Escribe carácter (AL) y color (AH) en VGA
    add di, 2       ; Siguiente celda (2 bytes)
    jmp .loop
.done:
    pop di
    ret
```

- **lodsb**: Instrucción de carga de string, automáticamente incrementa SI
- **[es:di]**: Acceso con direccionamiento indirecto usando ES:DI
- **ax = [color][carácter]**: Ambos bytes escritos simultáneamente

---

## Análisis: ¿Por Qué Esto No Es un Sistema Operativo?

| Aspecto | Bootloader | SO |
|---------|-----------|-----|
| **Tamaño** | 512 bytes | MBs/GBs |
| **Gestión de procesos** | ✗ | ✓ |
| **Multitarea** | ✗ | ✓ |
| **Protección memoria** | ✗ | ✓ |
| **Sistema de archivos** | ✗ | ✓ |
| **Drivers de hardware** | Mínimos | Extenso |
| **APIs de aplicación** | ✗ | ✓ |
| **Interfaz de usuario** | ✗ | ✓ (CLI/GUI) |
| **Abstracción hardware** | Mínima | Completa |

**Conclusión**: Este bootloader es un **programa de inicialización**, no un SO. Sirve para:
1. Demostrar el ciclo de arranque del BIOS
2. Ilustrar acceso directo a hardware (memoria VGA)
3. Mostrar cómo la CPU lee firmware y ejecuta código
4. Ser **base** (stage 1) de un SO real (que implementaría stage 2, kernel, etc.)

---

## Cómo Compilar y Ejecutar

### Opción 1: Con Make
```bash
cd ejercicio_01_bootloader_qemu
make          # Compila y ejecuta
make clean    # Limpia boot.bin
```

### Opción 2: Manual
```bash
nasm -f bin boot.asm -o boot.bin
qemu-system-i386 -drive format=raw,file=boot.bin -display gtk
```

---

## Requisitos Técnicos Cumplidos

✅ Archivo `boot.asm` en ensamblador x86 modo real  
✅ Compilación a binario booteable de 512 bytes  
✅ Firma de arranque `0x55AA` en bytes 510-511  
✅ Ejecución en QEMU con `qemu-system-i386`  
✅ Pantalla limpia y escritura en modo texto  
✅ Uso de BIOS interrupt `0x10` y memoria VGA `0xB8000`  
✅ Pantalla institucional con:
  - Título del curso
  - Nombre del grupo
  - ASCII art UTEM
  - 3 líneas explicativas sobre CPU, bootloader y SO
  - Uso de colores en memoria VGA  
✅ Makefile para compilación y ejecución  

---

## Referencias y Conceptos Relacionados

- **x86 Real Mode**: Modo de 16 bits, direccionamiento con Segment:Offset
- **Memory Segmentation**: Cálculo de dirección física = (Segment << 4) + Offset
- **BIOS Interrupts**: 0x10 (video), 0x13 (disco), 0x16 (teclado), etc.
- **VGA Text Mode**: Buffer de video en 0xB8000, atributos de color
- **Boot Sector**: 512 bytes, sector 0, cargado en 0x7C00
- **Little Endian vs Big Endian**: Intel x86 usa Little Endian

