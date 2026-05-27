@echo off
REM build.bat - Script de compilación para bootloader QEMU en Windows

setlocal enabledelayedexpansion

set "NASM=C:\Tools\NASM\nasm-2.15.05\nasm.exe"
set "QEMU=C:\Program Files\qemu\qemu-system-i386.exe"
set "SRC=boot.asm"
set "BIN=boot.bin"

if "%1"=="" (
    set "ACTION=all"
) else (
    set "ACTION=%1"
)

if "!ACTION!"=="all" (
    goto compile
) else if "!ACTION!"=="compile" (
    goto compile
) else if "!ACTION!"=="run" (
    goto run
) else if "!ACTION!"=="clean" (
    goto clean
) else (
    echo Uso: build.bat [compile^|run^|clean^|all]
    echo.
    echo  compile - Compila boot.asm a boot.bin
    echo  run     - Ejecuta boot.bin en QEMU
    echo  clean   - Elimina boot.bin
    echo  all     - Compila y ejecuta (default)
    exit /b 1
)

:compile
echo [*] Compilando %SRC%...

if not exist "%NASM%" (
    echo [!] Error: NASM no encontrado. Instala NASM primero.
    exit /b 1
)

%NASM% -f bin "%SRC%" -o "%BIN%" 2>&1
if %errorlevel% neq 0 (
    echo [!] Error durante la compilación
    exit /b 1
)

if exist "%BIN%" (
    for %%A in ("%BIN%") do set "SIZE=%%~zA"
    echo [+] Compilación exitosa: %BIN% (!SIZE! bytes)
    
    if !SIZE! equ 512 (
        echo [+] Tamaño correcto: 512 bytes
    )
    
    if "!ACTION!"=="compile" (
        exit /b 0
    )
) else (
    echo [!] Error: No se generó %BIN%
    exit /b 1
)

:run
if not exist "%BIN%" (
    echo [!] Error: %BIN% no existe. Compila primero.
    exit /b 1
)

if not exist "%QEMU%" (
    echo [!] Error: QEMU no encontrado en %QEMU%
    echo [!] Instala QEMU en C:\Program Files\qemu\
    exit /b 1
)

echo [*] Ejecutando QEMU...
echo [+] Se abrirá una ventana de QEMU. Usa Ctrl+Alt+G para liberar ratón.
"%QEMU%" -drive format=raw,file="%BIN%" -display gtk
exit /b 0

:clean
echo [*] Limpiando archivos...
if exist "%BIN%" (
    del /Q "%BIN%"
    echo [+] Limpieza completada
) else (
    echo [*] No hay archivos que limpiar
)
exit /b 0
