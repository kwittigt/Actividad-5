"""
pipeline/ingesta.py  —  Zona Bronze
Lee las fuentes crudas (CSV y JSONL), las copia sin transformación
a bronze/ en Parquet crudo y registra metadata básica.
"""
import json
import os
import sys
import shutil
from datetime import datetime, timezone
from typing import Dict

import pandas as pd
from rich.console import Console
from rich.table import Table

from pipeline.linaje import registrar_evento

console = Console()

# Asegura que el directorio raíz está en el path para resolver rutas
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BRONZE_DIR = "bronze"
# Construye la ruta absoluta a los datos para evitar FileNotFoundError
SEEDS_DIR  = os.path.join(ROOT, "data", "seeds")

# ── Rutas de entrada ──────────────────────────────────────────────────────────
FUENTES = {
    "transacciones": {
        "path": os.path.join(SEEDS_DIR, "transacciones.csv"),
        "format": "csv",
        "separador": ",",
    },
    "eventos": {
        "path": os.path.join(SEEDS_DIR, "eventos.jsonl"),
        "format": "jsonl",
    },
}


def leer_csv(path: str, sep: str = ",") -> pd.DataFrame:
    """Lee un CSV con tipos básicos sin castear."""
    df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    df["_source_file"] = os.path.basename(path)
    return df


def leer_jsonl(path: str) -> pd.DataFrame:
    """Lee un archivo JSONL línea por línea."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    df = pd.DataFrame(records).astype(str)
    # Reemplazar 'None' string → NaN
    df.replace("None", pd.NA, inplace=True)
    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    df["_source_file"] = os.path.basename(path)
    return df


def guardar_bronze(df: pd.DataFrame, nombre: str) -> str:
    """Guarda el DataFrame en bronze/ como Parquet sin partición."""
    os.makedirs(BRONZE_DIR, exist_ok=True)
    out_path = os.path.join(BRONZE_DIR, f"{nombre}.parquet")
    df.to_parquet(out_path, index=False, engine="pyarrow")
    return out_path


def copiar_raw(src: str, nombre: str) -> None:
    """Copia el archivo original a bronze/raw/ para trazabilidad."""
    raw_dir = os.path.join(BRONZE_DIR, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(raw_dir, os.path.basename(src)))


def ejecutar_ingesta() -> Dict[str, pd.DataFrame]:
    """
    Punto de entrada de la zona Bronze.
    Retorna un dict {nombre: DataFrame} para usarse en la siguiente zona.
    """
    console.rule("[bold yellow]ZONA BRONZE — Ingesta de datos crudos")
    resultados: Dict[str, pd.DataFrame] = {}

    tabla = Table(title="Resumen Bronze", show_lines=True)
    tabla.add_column("Fuente", style="cyan")
    tabla.add_column("Formato")
    tabla.add_column("Filas", justify="right")
    tabla.add_column("Columnas", justify="right")
    tabla.add_column("Destino", style="green")

    for nombre, cfg in FUENTES.items():
        path  = cfg["path"]
        fmt   = cfg["format"]

        console.print(f"\n  Leyendo [bold]{nombre}[/bold] desde [italic]{path}[/italic]")

        if fmt == "csv":
            df = leer_csv(path, sep=cfg.get("separador", ","))
        elif fmt == "jsonl":
            df = leer_jsonl(path)
        else:
            raise ValueError(f"Formato desconocido: {fmt}")

        out = guardar_bronze(df, nombre)
        copiar_raw(path, nombre)

        tabla.add_row(nombre, fmt.upper(), f"{len(df):,}", str(len(df.columns)), out)
        resultados[nombre] = df

        registrar_evento(
            origen=path,
            transformacion="ingesta_raw",
            destino=out,
            script="pipeline/ingesta.py",
            filas_entrada=len(df),
            filas_salida=len(df),
            notas=f"Lectura directa sin transformación — formato {fmt.upper()}",
        )

    console.print(tabla)
    console.print(f"\n  [green]✓ Bronze completado:[/green] {len(resultados)} fuentes ingestadas\n")
    return resultados
