"""
pipeline/main.py
Orquestador principal del pipeline Big Data local.
Ejecuta en orden:
  0. Generación de datos sintéticos
  1. Bronze  — Ingesta de datos crudos
  2. Silver  — Validación de calidad y limpieza
  3. Gold    — Transformaciones y agregaciones
  4. Queries — Consultas analíticas (DuckDB / Pandas / Polars)
  5. Catalog — Generación del catálogo de datos
  6. Lineage — Visualización del linaje registrado

Uso:
    python pipeline/main.py
    docker run --rm -v "$(pwd)":/work infb6074-pipeline
"""
import os
import sys
"""
pipeline/consultas.py
Ejecuta consultas analíticas sobre las tablas Gold y Silver.
"""

import argparse
import time
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel

# Asegura que el directorio raíz está en el path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

console = Console()


def encabezado() -> None:
    console.print(Panel.fit(
        "[bold white]Pipeline Big Data Local — INFB6074[/bold white]\n"
        "[dim]E-commerce Analytics · Bronze → Silver → Gold[/dim]\n"
        f"[dim]Inicio: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}[/dim]",
        border_style="bright_blue",
    ))


def paso(n: int, titulo: str) -> float:
    console.print()
    console.print(f"[bold bright_blue]{'─'*60}[/bold bright_blue]")
    console.print(f"[bold bright_blue]  PASO {n} — {titulo}[/bold bright_blue]")
    console.print(f"[bold bright_blue]{'─'*60}[/bold bright_blue]")
    return time.time()


def fin_paso(t0: float, titulo: str) -> None:
    elapsed = time.time() - t0
    console.print(f"  [dim]✓ {titulo} completado en {elapsed:.2f}s[/dim]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecutar el pipeline de datos de E-commerce.")
    parser.add_argument("--transacciones", type=int, default=5_000, help="Número de transacciones a generar.")
    parser.add_argument("--eventos", type=int, default=8_000, help="Número de eventos a generar.")
    parser.add_argument("--seed", type=int, default=42, help="Semilla para la generación de datos.")
    args = parser.parse_args()

    t_total = time.time()
    encabezado()

    # ── Paso 0: Generar datos sintéticos ────────────────────────────────────
    t0 = paso(0, "Generación de datos sintéticos")
    from data.generador import guardar_csv, guardar_jsonl, generar_transacciones, generar_eventos
    import random
    random.seed(args.seed)
    base = os.path.join(ROOT, "data", "seeds")
    console.print(f"  [dim]Generando {args.transacciones:,} transacciones y {args.eventos:,} eventos...[/dim]")
    txns   = generar_transacciones(args.transacciones)
    events = generar_eventos(args.eventos)
    guardar_csv(txns,   os.path.join(base, "transacciones.csv"))
    guardar_jsonl(events, os.path.join(base, "eventos.jsonl"))
    fin_paso(t0, "Generación de datos")

    # ── Paso 1: Bronze — Ingesta ─────────────────────────────────────────────
    t0 = paso(1, "Bronze — Ingesta de datos crudos")
    from pipeline.ingesta import ejecutar_ingesta
    bronces = ejecutar_ingesta()
    fin_paso(t0, "Ingesta Bronze")

    # ── Paso 2: Silver — Calidad ─────────────────────────────────────────────
    t0 = paso(2, "Silver — Validación de calidad y limpieza")
    from pipeline.calidad import ejecutar_calidad
    silvers = ejecutar_calidad(bronces)
    fin_paso(t0, "Validación Silver")

    # ── Paso 3: Gold — Transformaciones ──────────────────────────────────────
    t0 = paso(3, "Gold — Agregaciones analíticas")
    from pipeline.transformacion import ejecutar_transformacion
    golds = ejecutar_transformacion(silvers)
    fin_paso(t0, "Transformación Gold")

    # ── Paso 4: Consultas analíticas ─────────────────────────────────────────
    t0 = paso(4, "Consultas analíticas (DuckDB · Pandas · Polars)")
    from pipeline.consultas import ejecutar_consultas
    ejecutar_consultas(golds, silvers)
    fin_paso(t0, "Consultas analíticas")

    # ── Paso 5: Catálogo ─────────────────────────────────────────────────────
    t0 = paso(5, "Generación del catálogo de datos")
    from pipeline.catalogo import generar_catalogo
    generar_catalogo()
    fin_paso(t0, "Catálogo")

    # ── Paso 6: Linaje ───────────────────────────────────────────────────────
    t0 = paso(6, "Visualización del linaje registrado")
    from pipeline.linaje import imprimir_linaje
    imprimir_linaje()
    fin_paso(t0, "Linaje")

    # ── Resumen final ────────────────────────────────────────────────────────
    elapsed_total = time.time() - t_total
    console.print()
    console.print(Panel.fit(
        f"[bold green]✅ Pipeline completado exitosamente[/bold green]\n"
        f"[dim]Tiempo total: {elapsed_total:.1f}s[/dim]\n\n"
        "[white]Directorios de salida:[/white]\n"
        "  [cyan]bronze/[/cyan]    → datos crudos ingestados\n"
        "  [cyan]silver/[/cyan]    → datos limpios y tipados (Parquet particionado)\n"
        "  [cyan]gold/[/cyan]      → tablas analíticas agregadas\n"
        "  [cyan]metadata/[/cyan]  → catálogo.json + linaje.jsonl\n"
        "  [cyan]metrics/[/cyan]   → reporte_calidad.json + dashboard_analitico.png",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
