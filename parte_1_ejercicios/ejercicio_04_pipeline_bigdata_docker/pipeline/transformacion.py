"""
pipeline/transformacion.py  —  Zona Gold
Genera tablas analíticas agregadas a partir de los datos Silver:
  1. ventas_por_categoria_mes  — ingresos y unidades por categoría y mes
  2. usuarios_activos_resumen  — perfil de usuario: transacciones, gasto, eventos
  3. conversion_funnel          — embudo de conversión basado en eventos web
Guarda todas las salidas en gold/ como Parquet.
"""
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd
from rich.console import Console
from rich.table import Table

from pipeline.linaje import registrar_evento

console = Console()
GOLD_DIR = "gold"


# ─────────────────────────────────────────────────────────────────────────────
#  TABLA 1 — Ventas por categoría y mes
# ─────────────────────────────────────────────────────────────────────────────

def gold_ventas_categoria_mes(df_txn: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df_txn.groupby(["category", "year", "month", "country"], observed=True)
        .agg(
            total_ingresos=("amount",   "sum"),
            total_unidades=("quantity", "sum"),
            num_transacciones=("transaction_id", "count"),
            ticket_promedio=("amount",   "mean"),
        )
        .reset_index()
    )
    agg["total_ingresos"]   = agg["total_ingresos"].round(2)
    agg["ticket_promedio"]  = agg["ticket_promedio"].round(2)
    agg["_generated_at"]    = datetime.now(timezone.utc).isoformat()
    return agg.sort_values(["year", "month", "total_ingresos"], ascending=[True, True, False])


# ─────────────────────────────────────────────────────────────────────────────
#  TABLA 2 — Perfil de usuario (join transacciones + eventos)
# ─────────────────────────────────────────────────────────────────────────────

def gold_perfil_usuarios(df_txn: pd.DataFrame, df_evt: pd.DataFrame) -> pd.DataFrame:
    txn_user = (
        df_txn.groupby("user_id", observed=True)
        .agg(
            num_compras=("transaction_id", "count"),
            gasto_total=("amount", "sum"),
            gasto_promedio=("amount", "mean"),
            categorias_unicas=("category", "nunique"),
            primera_compra=("date", "min"),
            ultima_compra=("date", "max"),
        )
        .reset_index()
    )
    evt_user = (
        df_evt.groupby("user_id", observed=True)
        .agg(
            num_eventos=("event_id", "count"),
            sesiones_unicas=("session_id", "nunique"),
            dur_media_seg=("duration_sec", "mean"),
        )
        .reset_index()
    )
    perfil = txn_user.merge(evt_user, on="user_id", how="left")
    perfil["gasto_total"]    = perfil["gasto_total"].round(2)
    perfil["gasto_promedio"] = perfil["gasto_promedio"].round(2)
    perfil["dur_media_seg"]  = perfil["dur_media_seg"].round(2)
    perfil["_generated_at"]  = datetime.now(timezone.utc).isoformat()
    return perfil.sort_values("gasto_total", ascending=False)


# ─────────────────────────────────────────────────────────────────────────────
#  TABLA 3 — Embudo de conversión
# ─────────────────────────────────────────────────────────────────────────────

def gold_conversion_funnel(df_evt: pd.DataFrame) -> pd.DataFrame:
    STEPS = ["page_view", "search", "click", "add_to_cart", "purchase"]
    total_sesiones = df_evt["session_id"].nunique()

    rows = []
    for step in STEPS:
        sesiones_con_step = (
            df_evt[df_evt["event_type"] == step]["session_id"].nunique()
        )
        rows.append({
            "paso": step,
            "sesiones": sesiones_con_step,
            "pct_del_total": round(sesiones_con_step / max(total_sesiones, 1) * 100, 2),
        })

    funnel = pd.DataFrame(rows)
    funnel["sesiones_previas"] = funnel["sesiones"].shift(1)
    funnel["tasa_conversion_paso"] = (
        funnel["sesiones"] / funnel["sesiones_previas"].replace(0, pd.NA) * 100
    ).round(2)
    funnel["_generated_at"] = datetime.now(timezone.utc).isoformat()
    return funnel


# ─────────────────────────────────────────────────────────────────────────────
#  GUARDAR
# ─────────────────────────────────────────────────────────────────────────────

def guardar_gold(df: pd.DataFrame, nombre: str,
                 partition_cols: Optional[List[str]] = None) -> str:
    os.makedirs(GOLD_DIR, exist_ok=True)
    if partition_cols:
        out = os.path.join(GOLD_DIR, nombre)
        df.to_parquet(out, index=False, partition_cols=partition_cols,
                      engine="pyarrow", existing_data_behavior="delete_matching")
    else:
        out = os.path.join(GOLD_DIR, f"{nombre}.parquet")
        df.to_parquet(out, index=False, engine="pyarrow")
    return out


def _preview(df: pd.DataFrame, titulo: str, n: int = 5) -> None:
    tabla = Table(title=f"{titulo}  ({len(df):,} filas)", show_lines=True)
    for col in df.columns[:8]:  # max 8 columnas para legibilidad
        tabla.add_column(str(col), overflow="fold")
    for _, row in df.head(n).iterrows():
        tabla.add_row(*[str(v)[:30] for v in row.values[:8]])
    console.print(tabla)


# ─────────────────────────────────────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────

def ejecutar_transformacion(silvers: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    console.rule("[bold magenta]ZONA GOLD — Agregaciones analíticas")

    df_txn = silvers["transacciones"]
    df_evt = silvers["eventos"]

    # Tabla 1
    console.print("\n[bold]▸ Generando: ventas_categoria_mes[/bold]")
    df_ventas = gold_ventas_categoria_mes(df_txn)
    path1 = guardar_gold(df_ventas, "ventas_categoria_mes",
                         partition_cols=["year", "month"])
    _preview(df_ventas, "Ventas por Categoría/Mes")
    registrar_evento(
        origen="silver/transacciones",
        transformacion="aggregation_ventas_categoria_mes",
        destino=path1,
        script="pipeline/transformacion.py",
        filas_entrada=len(df_txn),
        filas_salida=len(df_ventas),
        notas="GROUP BY category, year, month, country",
    )

    # Tabla 2
    console.print("[bold]▸ Generando: perfil_usuarios[/bold]")
    df_perfil = gold_perfil_usuarios(df_txn, df_evt)
    path2 = guardar_gold(df_perfil, "perfil_usuarios")
    _preview(df_perfil, "Perfil de Usuarios")
    registrar_evento(
        origen="silver/transacciones + silver/eventos",
        transformacion="join_perfil_usuarios",
        destino=path2,
        script="pipeline/transformacion.py",
        filas_entrada=len(df_txn) + len(df_evt),
        filas_salida=len(df_perfil),
        notas="LEFT JOIN transacciones-usuarios con eventos-usuarios",
    )

    # Tabla 3
    console.print("[bold]▸ Generando: conversion_funnel[/bold]")
    df_funnel = gold_conversion_funnel(df_evt)
    path3 = guardar_gold(df_funnel, "conversion_funnel")
    _preview(df_funnel, "Embudo de Conversión")
    registrar_evento(
        origen="silver/eventos",
        transformacion="conversion_funnel_by_session",
        destino=path3,
        script="pipeline/transformacion.py",
        filas_entrada=len(df_evt),
        filas_salida=len(df_funnel),
        notas="Embudo: page_view → search → click → add_to_cart → purchase",
    )

    console.print(f"\n  [green]✓ Gold completado:[/green] 3 tablas analíticas\n")
    return {
        "ventas_categoria_mes": df_ventas,
        "perfil_usuarios": df_perfil,
        "conversion_funnel": df_funnel,
    }
