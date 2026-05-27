"""
pipeline/consultas.py
Ejecuta consultas analíticas sobre las tablas Gold y Silver.
"""

"""
pipeline/consultas.py
Ejecuta consultas analíticas sobre los datos Gold usando:
  - DuckDB  (SQL sobre Parquet directamente)
  - Pandas  (operaciones vectorizadas)
  - Polars  (procesamiento columnar lazy)
Genera visualizaciones y guarda resultados en metrics/.
"""
import os
from datetime import datetime, timezone
from typing import Dict #

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import polars as pl
from rich.console import Console
from rich.table import Table

console = Console()
METRICS_DIR = "metrics"
GOLD_DIR    = "gold"


# ─────────────────────────────────────────────────────────────────────────────
#  CONSULTA 1 — DuckDB: Top 5 categorías por ingreso total
# ─────────────────────────────────────────────────────────────────────────────

def consulta_1_duckdb_top_categorias() -> pd.DataFrame:
    console.print("\n[bold cyan]◆ Consulta 1 (DuckDB)[/bold cyan] — Top categorías por ingresos")
    parquet_path = os.path.join(GOLD_DIR, "ventas_categoria_mes")

    con = duckdb.connect()
    sql = f"""
        SELECT
            category,
            SUM(total_ingresos)      AS ingresos_totales,
            SUM(total_unidades)      AS unidades_totales,
            SUM(num_transacciones)   AS num_transacciones,
            AVG(ticket_promedio)     AS ticket_promedio,
            COUNT(DISTINCT country)  AS num_paises
        FROM read_parquet('{parquet_path}/**/*.parquet', hive_partitioning=true)
        GROUP BY category
        ORDER BY ingresos_totales DESC
        LIMIT 10
    """
    df = con.execute(sql).df()
    con.close()

    _mostrar_tabla_rich(df, "Top Categorías — DuckDB")
    return df


# ─────────────────────────────────────────────────────────────────────────────
#  CONSULTA 2 — DuckDB: Serie temporal mensual de ingresos
# ─────────────────────────────────────────────────────────────────────────────

def consulta_2_duckdb_serie_temporal() -> pd.DataFrame:
    console.print("\n[bold cyan]◆ Consulta 2 (DuckDB)[/bold cyan] — Serie temporal de ingresos mensuales")
    parquet_path = os.path.join(GOLD_DIR, "ventas_categoria_mes")

    con = duckdb.connect()
    sql = f"""
        WITH base AS (
            SELECT
                year,
                month,
                printf('%d-%02d', year, month)  AS periodo,
                SUM(total_ingresos)             AS ingresos_mes,
                SUM(num_transacciones)          AS transacciones_mes
            FROM read_parquet('{parquet_path}/**/*.parquet', hive_partitioning=true)
            GROUP BY year, month
        )
        SELECT
            *,
            SUM(ingresos_mes) OVER (ORDER BY year, month
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS ingresos_acum
        FROM base
        ORDER BY year, month
    """
    df = con.execute(sql).df()
    con.close()

    _mostrar_tabla_rich(df, "Serie Temporal Mensual — DuckDB")
    return df


# ─────────────────────────────────────────────────────────────────────────────
#  CONSULTA 3 — Pandas: Segmentación RFM simplificada
# ─────────────────────────────────────────────────────────────────────────────

def consulta_3_pandas_rfm() -> pd.DataFrame:
    console.print("\n[bold green]◆ Consulta 3 (Pandas)[/bold green] — Segmentación RFM de usuarios")
    parquet_path = os.path.join(GOLD_DIR, "perfil_usuarios.parquet")
    df = pd.read_parquet(parquet_path)

    # Calcular quintiles R, F, M
    df["R_score"] = pd.qcut(df["ultima_compra"].rank(method="first"),
                            q=5, labels=[1, 2, 3, 4, 5])
    df["F_score"] = pd.qcut(df["num_compras"].rank(method="first"),
                            q=5, labels=[1, 2, 3, 4, 5])
    df["M_score"] = pd.qcut(df["gasto_total"].rank(method="first"),
                            q=5, labels=[1, 2, 3, 4, 5])

    df["RFM_total"] = (
        df["R_score"].astype(int) +
        df["F_score"].astype(int) +
        df["M_score"].astype(int)
    )

    # Segmentar
    def segmento(rfm):
        if rfm >= 12: return "Campeón"
        if rfm >= 9:  return "Leal"
        if rfm >= 6:  return "Potencial"
        return "En Riesgo"

    df["segmento"] = df["RFM_total"].apply(segmento)

    resumen = (
        df.groupby("segmento", observed=True)
        .agg(
            num_usuarios=("user_id", "count"),
            gasto_medio=("gasto_total", "mean"),
            compras_medias=("num_compras", "mean"),
        )
        .reset_index()
        .sort_values("gasto_medio", ascending=False)
    )
    resumen["gasto_medio"]   = resumen["gasto_medio"].round(2)
    resumen["compras_medias"] = resumen["compras_medias"].round(2)

    _mostrar_tabla_rich(resumen, "Segmentación RFM — Pandas")
    return df, resumen


# ─────────────────────────────────────────────────────────────────────────────
#  CONSULTA 4 — Polars: Análisis de comportamiento por dispositivo
# ─────────────────────────────────────────────────────────────────────────────

def consulta_4_polars_dispositivos(df_evt_pd: pd.DataFrame) -> pl.DataFrame:
    console.print("\n[bold yellow]◆ Consulta 4 (Polars)[/bold yellow] — Comportamiento por dispositivo")

    df_pl = pl.from_pandas(df_evt_pd[["device", "browser", "event_type",
                                       "duration_sec", "session_id"]].copy())

    resultado = (
        df_pl
        .lazy()
        .group_by(["device", "browser"])
        .agg([
            pl.count("session_id").alias("num_sesiones"),
            pl.n_unique("session_id").alias("sesiones_unicas"),
            pl.mean("duration_sec").round(2).alias("dur_media_seg"),
            pl.max("duration_sec").alias("dur_max_seg"),
            (pl.col("event_type") == "purchase").sum().alias("num_compras"),
        ])
        .sort("num_sesiones", descending=True)
        .collect()
    )

    # Mostrar como tabla
    df_show = resultado.to_pandas()
    _mostrar_tabla_rich(df_show, "Comportamiento por Dispositivo/Browser — Polars")
    return resultado


# ─────────────────────────────────────────────────────────────────────────────
#  CONSULTA 5 — DuckDB: Análisis geográfico de ventas
# ─────────────────────────────────────────────────────────────────────────────

def consulta_5_duckdb_geografico() -> pd.DataFrame:
    console.print("\n[bold cyan]◆ Consulta 5 (DuckDB)[/bold cyan] — Desempeño por país")
    parquet_path = os.path.join(GOLD_DIR, "ventas_categoria_mes")

    con = duckdb.connect()
    sql = f"""
        SELECT
            country,
            SUM(total_ingresos)                             AS ingresos_totales,
            SUM(num_transacciones)                          AS num_transacciones,
            AVG(ticket_promedio)                            AS ticket_promedio,
            100.0 * SUM(total_ingresos)
              / SUM(SUM(total_ingresos)) OVER ()            AS pct_ingresos
        FROM read_parquet('{parquet_path}/**/*.parquet', hive_partitioning=true)
        GROUP BY country
        ORDER BY ingresos_totales DESC
    """
    df = con.execute(sql).df()
    df["ticket_promedio"] = df["ticket_promedio"].round(2)
    df["pct_ingresos"]    = df["pct_ingresos"].round(2)
    con.close()

    _mostrar_tabla_rich(df, "Análisis Geográfico — DuckDB")
    return df


# ─────────────────────────────────────────────────────────────────────────────
#  VISUALIZACIONES
# ─────────────────────────────────────────────────────────────────────────────

def generar_visualizaciones(
    df_top_cat:    pd.DataFrame,
    df_serie:      pd.DataFrame,
    df_rfm:        pd.DataFrame,
    df_funnel_pd:  pd.DataFrame,
    df_geo:        pd.DataFrame,
) -> None:
    os.makedirs(METRICS_DIR, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    fig.suptitle("Dashboard Analítico — E-commerce Pipeline", fontsize=15, fontweight="bold")

    # 1 — Barras horizontales: ingresos por categoría
    ax = axes[0, 0]
    cats = df_top_cat.sort_values("ingresos_totales")
    ax.barh(cats["category"], cats["ingresos_totales"] / 1_000, color="#4C72B0")
    ax.set_title("Ingresos por Categoría (USD k)")
    ax.set_xlabel("USD miles")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}k"))

    # 2 — Línea: serie temporal de ingresos
    ax = axes[0, 1]
    if len(df_serie) > 0:
        ax.plot(range(len(df_serie)), df_serie["ingresos_mes"] / 1_000,
                marker="o", color="#DD8452", linewidth=2)
        ax.set_xticks(range(len(df_serie)))
        step = max(1, len(df_serie) // 6)
        labels = [p if i % step == 0 else "" for i, p in enumerate(df_serie["periodo"])]
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_title("Ingresos Mensuales (USD k)")
        ax.set_ylabel("USD miles")

    # 3 — Torta: segmentos RFM
    ax = axes[0, 2]
    seg_counts = df_rfm["segmento"].value_counts()
    colors = ["#55A868", "#4C72B0", "#C44E52", "#8172B2"]
    ax.pie(seg_counts.values, labels=seg_counts.index, autopct="%1.1f%%",
           colors=colors[:len(seg_counts)], startangle=90)
    ax.set_title("Segmentación RFM de Usuarios")

    # 4 — Embudo de conversión
    ax = axes[1, 0]
    if len(df_funnel_pd) > 0:
        pasos = df_funnel_pd["paso"]
        pcts  = df_funnel_pd["pct_del_total"]
        bars  = ax.barh(pasos[::-1], pcts[::-1], color="#64B5CD")
        ax.set_title("Embudo de Conversión (%)")
        ax.set_xlabel("% de sesiones")
        for bar, pct in zip(bars, pcts[::-1]):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                    f"{pct:.1f}%", va="center")

    # 5 — Mapa de calor: ingresos por país y categoría
    ax = axes[1, 1]
    parquet_path = os.path.join(GOLD_DIR, "ventas_categoria_mes")
    try:
        con = duckdb.connect()
        hm_df = con.execute(f"""
            SELECT country, category, SUM(total_ingresos) AS ingresos
            FROM read_parquet('{parquet_path}/**/*.parquet', hive_partitioning=true)
            GROUP BY country, category
        """).df()
        con.close()
        pivot = hm_df.pivot_table(index="country", columns="category",
                                  values="ingresos", fill_value=0)
        im = ax.imshow(pivot.values / 1_000, aspect="auto", cmap="Blues")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)
        ax.set_title("Ingresos País × Categoría (USD k)")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    except Exception:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")

    # 6 — Barras: ingresos por país
    ax = axes[1, 2]
    df_geo_s = df_geo.sort_values("ingresos_totales", ascending=True)
    ax.barh(df_geo_s["country"], df_geo_s["ingresos_totales"] / 1_000,
            color="#C44E52")
    ax.set_title("Ingresos Totales por País (USD k)")
    ax.set_xlabel("USD miles")

    plt.tight_layout()
    out = os.path.join(METRICS_DIR, "dashboard_analitico.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    console.print(f"\n  [green]✓ Dashboard guardado:[/green] {out}")


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _mostrar_tabla_rich(df: pd.DataFrame, titulo: str) -> None:
    tabla = Table(title=titulo, show_lines=True)
    for col in df.columns:
        tabla.add_column(str(col), overflow="fold")
    for _, row in df.head(10).iterrows():
        tabla.add_row(*[str(round(v, 2)) if isinstance(v, float) else str(v)
                        for v in row.values])
    console.print(tabla)


def guardar_resultados(dfs: Dict[str, pd.DataFrame]) -> None:
    os.makedirs(METRICS_DIR, exist_ok=True)
    for nombre, df in dfs.items():
        if isinstance(df, pd.DataFrame):
            path = os.path.join(METRICS_DIR, f"query_{nombre}.parquet")
            df.to_parquet(path, index=False)
    console.print(f"\n  [green]✓ Resultados de consultas guardados en metrics/[/green]")


# ─────────────────────────────────────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────

def ejecutar_consultas(golds: Dict[str, pd.DataFrame],
                       silvers: Dict[str, pd.DataFrame]) -> None:
    console.rule("[bold red]CONSULTAS ANALÍTICAS — DuckDB · Pandas · Polars")

    df_top_cat  = consulta_1_duckdb_top_categorias()
    df_serie    = consulta_2_duckdb_serie_temporal()
    df_rfm_full, df_rfm_seg = consulta_3_pandas_rfm()
    df_device   = consulta_4_polars_dispositivos(silvers["eventos"])
    df_geo      = consulta_5_duckdb_geografico()

    df_funnel_pd = golds.get("conversion_funnel", pd.DataFrame())

    generar_visualizaciones(df_top_cat, df_serie, df_rfm_full,
                            df_funnel_pd, df_geo)

    guardar_resultados({
        "top_categorias": df_top_cat,
        "serie_temporal":  df_serie,
        "rfm_segmentos":   df_rfm_seg,
        "geo":             df_geo,
    })
