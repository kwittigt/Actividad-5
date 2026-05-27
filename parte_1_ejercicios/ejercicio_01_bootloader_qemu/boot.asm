[BITS 16]           ; Indicamos al compilador que genere código de 16 bits (Modo Real)
[ORG 0x7C00]        ; El BIOS cargará el bootloader en la dirección de memoria 0x7C00

start:
    ; 1. Inicializar segmentos de memoria
    cli             ; Deshabilitar interrupciones por seguridad
    xor ax, ax      ; AX = 0
    mov ds, ax      ; Data Segment = 0
    mov es, ax      ; Extra Segment = 0
    mov ss, ax      ; Stack Segment = 0
    mov sp, 0x7C00  ; El stack crece hacia abajo, seguro antes de 0x7C00
    sti             ; Habilitar interrupciones

    ; 2. Limpiar pantalla usando el BIOS (Modo texto 80x25)
    mov ah, 0x00    ; Función de BIOS: Cambiar modo de video
    mov al, 0x03    ; Modo 3: Texto 80x25, 16 colores
    int 0x10        ; Interrupción de servicios de video del BIOS

    ; 3. Configurar escritura directa a memoria VGA
    mov ax, 0xB800  ; Dirección del buffer de texto VGA
    mov es, ax      ; Guardamos la dirección en el Extra Segment

    ; --- IMPRESIÓN EN PANTALLA ---

    ; Título del curso (Cyan claro sobre negro)
    mov si, title_str
    mov ah, 0x0B     
    mov di, 160 * 2 + 25 * 2 ; Fila 2, Columna 25
    call print_str

    ; Nombre del grupo (Verde claro sobre negro)
    mov si, group_str
    mov ah, 0x0A     
    mov di, 160 * 4 + 28 * 2 ; Fila 4, Columna 28
    call print_str

    ; Emblema/ASCII Art UTEM (Amarillo sobre negro)
    mov ah, 0x0E     
    mov si, utem_1
    mov di, 160 * 7 + 28 * 2
    call print_str
    mov si, utem_2
    mov di, 160 * 8 + 28 * 2
    call print_str
    mov si, utem_3
    mov di, 160 * 9 + 28 * 2
    call print_str
    mov si, utem_4
    mov di, 160 * 10 + 28 * 2
    call print_str
    mov si, utem_5
    mov di, 160 * 11 + 28 * 2
    call print_str

    ; 3 líneas explicativas (Blanco sobre negro)
    mov ah, 0x0F     
    mov si, line1_str
    mov di, 160 * 15 + 10 * 2
    call print_str
    
    mov si, line2_str
    mov di, 160 * 17 + 10 * 2
    call print_str
    
    mov si, line3_str
    mov di, 160 * 19 + 10 * 2
    call print_str

halt:
    hlt             ; Detiene la CPU hasta la próxima interrupción
    jmp halt        ; Bucle infinito (evita que el procesador ejecute basura)

; --- RUTINA DE IMPRESIÓN DIRECTA EN VGA ---
; Entradas: SI = String, AH = Color, DI = Offset de pantalla
print_str:
    push di         ; Guardar la posición actual
.loop:
    lodsb           ; Carga el byte de [DS:SI] en AL y avanza SI
    or al, al       ; Comprueba si AL es 0 (fin de string)
    jz .done        ; Si es 0, termina
    mov [es:di], ax ; Escribe AL (carácter) y AH (color) en VGA
    add di, 2       ; Avanza 2 bytes (1 celda de memoria de video)
    jmp .loop
.done:
    pop di
    ret

; --- DATOS Y STRINGS (Terminados en nulo '0') ---
title_str db "SISTEMAS OPERATIVOS", 0
group_str db "GRUPO: LOS KERNELS", 0

utem_1    db "U   U TTTTT EEEEE M   M", 0
utem_2    db "U   U   T   E     MM MM", 0
utem_3    db "U   U   T   EEE   M M M", 0
utem_4    db "U   U   T   E     M   M", 0
utem_5    db " UUU    T   EEEEE M   M", 0

line1_str db "-> CPU: Ejecuta las instrucciones basicas desde la memoria.", 0
line2_str db "-> Bootloader: Carga en 0x7C00 para iniciar el sistema.", 0
line3_str db "-> SO: Abstrae el hardware y administra los recursos.", 0

; --- FIRMA DE ARRANQUE ---
times 510-($-$$) db 0   ; Rellena con ceros hasta llegar a los 510 bytes
dw 0xAA55               ; Firma mágica de 2 bytes (0x55AA en Little Endian)