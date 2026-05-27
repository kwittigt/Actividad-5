"""
pipeline/linaje.py
Registra el linaje de datos en metadata/linaje.jsonl.
Cada evento incluye: origen, transformación, destino,
fecha de ejecución, script responsable y estadísticas básicas.
"""
import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict

LINAJE_FILE = os.path.join("metadata", "linaje.jsonl")


def registrar_evento(
    origen: str,
    transformacion: str,
    destino: str,
    script: str,
    filas_entrada: int = 0,
    filas_salida: int = 0,
    notas: str = "",
) -> None:
    """Agrega un registro de linaje al archivo JSONL."""
    os.makedirs("metadata", exist_ok=True)
    evento = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "origen": origen,
        "transformacion": transformacion,
        "destino": destino,
        "script_responsable": script,
        "filas_entrada": filas_entrada,
        "filas_salida": filas_salida,
        "filas_eliminadas": max(0, filas_entrada - filas_salida),
        "notas": notas,
    }
    with open(LINAJE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")


def leer_linaje() -> List[Dict]:
    """Lee todos los eventos de linaje registrados."""
    if not os.path.exists(LINAJE_FILE):
        return []
    
    eventos = []
    with open(LINAJE_FILE, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                eventos.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"[ADVERTENCIA] Se omite la línea {i} corrupta en el archivo de linaje.", file=sys.stderr)
    return eventos


def imprimir_linaje() -> None:
    """Imprime el linaje en formato tabular."""
    import pandas as pd
    from rich.console import Console
    from rich.table import Table

    console = Console()
    eventos = leer_linaje()
    if not eventos:
        console.print("[yellow]No hay eventos de linaje registrados.[/yellow]")
        return

    tabla = Table(title="Linaje de Datos", show_lines=True)
    for col in ["timestamp_utc", "origen", "transformacion", "destino",
                "script_responsable", "filas_entrada", "filas_salida", "filas_eliminadas"]:
        tabla.add_column(col, overflow="fold")

    for e in eventos:
        tabla.add_row(
            e.get("timestamp_utc", "")[:19],
            os.path.basename(e.get("origen", "")),
            e.get("transformacion", ""),
            os.path.basename(e.get("destino", "")),
            os.path.basename(e.get("script_responsable", "")),
            str(e.get("filas_entrada", 0)),
            str(e.get("filas_salida", 0)),
            str(e.get("filas_eliminadas", 0)),
        )

    console.print(tabla)
