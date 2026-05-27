"""
pipeline/calidad.py  —  Zona Silver
Aplica reglas de calidad, genera reporte, limpia los datos
y escribe silver/ en Parquet particionado.

Reglas implementadas:
  R01 — Nulos en campos obligatorios
  R02 — Duplicados en clave primaria
  R03 — Rangos inválidos (amount, quantity, duration_sec)
  R04 — Categorías no permitidas (category, payment_method, event_type)
  R05 — Fechas futuras
  R06 — Integridad referencial (user_id eventos vs transacciones)
  R07 — Longitud/formato de identificadores
  R08 — Outliers estadísticos en amount (IQR)
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

from pipeline.linaje import registrar_evento

console = Console()

SILVER_DIR   = "silver"
METRICS_DIR  = "metrics"

# ── Catálogo de valores permitidos ───────────────────────────────────────────
CATEGORIAS_OK     = {"Electrónica", "Ropa", "Hogar", "Deportes", "Libros", "Juguetes"}
METODOS_PAGO_OK   = {"tarjeta_credito", "tarjeta_debito", "transferencia", "efectivo", "billetera_digital"}
ESTADOS_OK        = {"completada", "pendiente", "cancelada", "reembolsada"}
PAISES_OK         = {"CL", "AR", "MX", "CO", "PE", "BR"}
EVENTOS_OK        = {"page_view", "click", "add_to_cart", "purchase", "search", "logout"}
DISPOSITIVOS_OK   = {"mobile", "desktop", "tablet"}

HOY = datetime.now(timezone.utc).replace(tzinfo=None)

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _flag(df: pd.DataFrame, mask: pd.Series, regla: str, descripcion: str,
          reporte: list) -> None:
    """Registra violaciones encontradas en el reporte."""
    n = int(mask.sum())
    reporte.append({
        "regla": regla,
        "descripcion": descripcion,
        "violaciones": n,
        "porcentaje": round(n / max(len(df), 1) * 100, 2),
        "accion": "eliminar fila" if n > 0 else "—",
    })


# ─────────────────────────────────────────────────────────────────────────────
#  VALIDACIÓN TRANSACCIONES
# ─────────────────────────────────────────────────────────────────────────────

def validar_transacciones(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, List]:
    reporte = []
    df = df_raw.copy()

    # Casteo básico (bronze llega todo como str)
    df["amount"]   = pd.to_numeric(df["amount"],   errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["date"]     = pd.to_datetime(df["date"],    errors="coerce")

    # R01 — Nulos en campos obligatorios
    campos_oblig = ["transaction_id", "user_id", "product_id", "amount", "date", "country"]
    mask_nulos = df[campos_oblig].isnull().any(axis=1)
    _flag(df, mask_nulos, "R01", "Nulos en campos obligatorios", reporte)

    # R02 — Duplicados en transaction_id
    mask_dup = df.duplicated(subset=["transaction_id"], keep="first")
    _flag(df, mask_dup, "R02", "Duplicados en transaction_id (clave primaria)", reporte)

    # R03a — amount negativo o cero
    mask_amount = df["amount"].notna() & (df["amount"] <= 0)
    _flag(df, mask_amount, "R03a", "amount ≤ 0 (rango inválido)", reporte)

    # R03b — quantity negativa
    mask_qty = df["quantity"].notna() & (df["quantity"] <= 0)
    _flag(df, mask_qty, "R03b", "quantity ≤ 0 (rango inválido)", reporte)

    # R04 — Categorías no permitidas
    mask_cat = df["category"].notna() & ~df["category"].isin(CATEGORIAS_OK)
    _flag(df, mask_cat, "R04a", f"category no permitida (esperado: {sorted(CATEGORIAS_OK)})", reporte)

    mask_pago = df["payment_method"].notna() & ~df["payment_method"].isin(METODOS_PAGO_OK)
    _flag(df, mask_pago, "R04b", f"payment_method no permitido", reporte)

    # R05 — Fechas futuras
    mask_fecha = df["date"].notna() & (df["date"] > HOY)
    _flag(df, mask_fecha, "R05", "date superior a la fecha actual (fecha futura)", reporte)

    # R07 — Formato de transaction_id (patrón TXN-XXXXXX)
    mask_fmt = ~df["transaction_id"].str.match(r"^TXN-\d{6}$", na=False)
    _flag(df, mask_fmt, "R07", "transaction_id con formato inválido (esperado TXN-XXXXXX)", reporte)

    # R08 — Outliers estadísticos en amount (> Q3 + 3*IQR)
    q1, q3 = df["amount"].quantile([0.25, 0.75])
    iqr = q3 - q1
    mask_outlier = df["amount"].notna() & (df["amount"] > q3 + 3 * iqr)
    _flag(df, mask_outlier, "R08", f"amount outlier extremo (> Q3+3·IQR = {q3+3*iqr:.2f})", reporte)

    # ── FILTRADO (eliminar filas inválidas) ────────────────────────────────
    mask_invalida = (
        mask_nulos | mask_dup | mask_amount | mask_qty |
        mask_cat  | mask_pago | mask_fecha  | mask_fmt
    )
    df_clean = df[~mask_invalida].copy()

    # Normalizar tipos finales
    df_clean["date"] = pd.to_datetime(df_clean["date"])
    df_clean["amount"]   = df_clean["amount"].astype(float)
    df_clean["quantity"] = df_clean["quantity"].astype(int)
    df_clean["year"]     = df_clean["date"].dt.year
    df_clean["month"]    = df_clean["date"].dt.month

    return df_clean, reporte


# ─────────────────────────────────────────────────────────────────────────────
#  VALIDACIÓN EVENTOS
# ─────────────────────────────────────────────────────────────────────────────

def validar_eventos(df_raw: pd.DataFrame,
                    user_ids_validos: set) -> Tuple[pd.DataFrame, List]:
    reporte = []
    df = df_raw.copy()

    df["duration_sec"] = pd.to_numeric(df["duration_sec"], errors="coerce")
    df["timestamp"]    = pd.to_datetime(df["timestamp"],   errors="coerce")

    # R01 — Nulos en campos obligatorios
    campos_oblig = ["event_id", "user_id", "session_id", "event_type", "timestamp"]
    mask_nulos = df[campos_oblig].isnull().any(axis=1)
    _flag(df, mask_nulos, "R01", "Nulos en campos obligatorios", reporte)

    # R02 — Duplicados en event_id
    mask_dup = df.duplicated(subset=["event_id"], keep="first")
    _flag(df, mask_dup, "R02", "Duplicados en event_id (clave primaria)", reporte)

    # R03 — duration_sec negativa
    mask_dur = df["duration_sec"].notna() & (df["duration_sec"] < 0)
    _flag(df, mask_dur, "R03", "duration_sec < 0 (rango inválido)", reporte)

    # R04a — event_type no permitido
    mask_evt = df["event_type"].notna() & ~df["event_type"].isin(EVENTOS_OK)
    _flag(df, mask_evt, "R04a", f"event_type no permitido (esperado: {sorted(EVENTOS_OK)})", reporte)

    # R04b — device no permitido
    mask_dev = df["device"].notna() & ~df["device"].isin(DISPOSITIVOS_OK)
    _flag(df, mask_dev, "R04b", "device no permitido", reporte)

    # R05 — Timestamps futuros
    mask_fut = df["timestamp"].notna() & (df["timestamp"] > HOY)
    _flag(df, mask_fut, "R05", "timestamp superior a fecha actual (futuro)", reporte)

    # R06 — Integridad referencial user_id
    mask_ref = df["user_id"].notna() & ~df["user_id"].isin(user_ids_validos)
    _flag(df, mask_ref, "R06", "user_id en eventos no existe en transacciones (integridad referencial)", reporte)

    # R07 — Formato event_id
    mask_fmt = ~df["event_id"].str.match(r"^EVT-\d{7}$", na=False)
    _flag(df, mask_fmt, "R07", "event_id con formato inválido (esperado EVT-XXXXXXX)", reporte)

    # ── FILTRADO ────────────────────────────────────────────────────────────
    mask_invalida = (
        mask_nulos | mask_dup | mask_dur | mask_evt |
        mask_dev  | mask_fut  | mask_ref | mask_fmt
    )
    df_clean = df[~mask_invalida].copy()

    df_clean["timestamp"]    = pd.to_datetime(df_clean["timestamp"])
    df_clean["duration_sec"] = df_clean["duration_sec"].astype(float)
    df_clean["year"]         = df_clean["timestamp"].dt.year
    df_clean["month"]        = df_clean["timestamp"].dt.month

    return df_clean, reporte


# ─────────────────────────────────────────────────────────────────────────────
#  GUARDAR SILVER + REPORTE
# ─────────────────────────────────────────────────────────────────────────────

def guardar_silver(df: pd.DataFrame, nombre: str,
                   partition_cols: Optional[List[str]] = None) -> str:
    os.makedirs(SILVER_DIR, exist_ok=True)
    out_dir = os.path.join(SILVER_DIR, nombre)

    if partition_cols:
        df.to_parquet(out_dir, index=False, partition_cols=partition_cols,
                      engine="pyarrow", existing_data_behavior="delete_matching")
        return out_dir
    else:
        out_path = os.path.join(SILVER_DIR, f"{nombre}.parquet")
        df.to_parquet(out_path, index=False, engine="pyarrow")
        return out_path


def guardar_reporte_calidad(reporte_txn: list, reporte_evt: list,
                             stats_txn: dict, stats_evt: dict) -> None:
    os.makedirs(METRICS_DIR, exist_ok=True)

    reporte_completo = {
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "transacciones": {
            "estadisticas": stats_txn,
            "reglas": reporte_txn,
        },
        "eventos": {
            "estadisticas": stats_evt,
            "reglas": reporte_evt,
        },
    }
    path = os.path.join(METRICS_DIR, "reporte_calidad.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reporte_completo, f, ensure_ascii=False, indent=2)
    console.print(f"\n  [green]✓ Reporte de calidad guardado:[/green] {path}")


def _mostrar_reporte(titulo: str, reporte: list, n_in: int, n_out: int) -> None:
    tabla = Table(title=titulo, show_lines=True)
    tabla.add_column("Regla",      style="cyan", width=8)
    tabla.add_column("Descripción", overflow="fold", width=50)
    tabla.add_column("Violaciones", justify="right")
    tabla.add_column("%", justify="right")
    tabla.add_column("Acción")

    for r in reporte:
        color = "red" if r["violaciones"] > 0 else "green"
        tabla.add_row(
            r["regla"],
            r["descripcion"],
            f"[{color}]{r['violaciones']:,}[/{color}]",
            f"[{color}]{r['porcentaje']}%[/{color}]",
            r["accion"],
        )
    console.print(tabla)
    tasa = round((n_in - n_out) / max(n_in, 1) * 100, 2)
    console.print(f"  Filas entrada: [bold]{n_in:,}[/bold]  →  "
                  f"Filas limpias: [bold green]{n_out:,}[/bold green]  "
                  f"([red]{tasa}% eliminadas[/red])\n")


# ─────────────────────────────────────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────

def ejecutar_calidad(bronces: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    console.rule("[bold blue]ZONA SILVER — Validación de calidad y limpieza")

    df_txn_raw = bronces["transacciones"]
    df_evt_raw = bronces["eventos"]

    # Validar transacciones
    console.print("\n[bold]▸ Transacciones[/bold]")
    df_txn, rep_txn = validar_transacciones(df_txn_raw)
    _mostrar_reporte("Reglas — Transacciones", rep_txn,
                     len(df_txn_raw), len(df_txn))

    # Extraer user_ids válidos para validación referencial
    user_ids_validos = set(df_txn["user_id"].dropna().unique())

    # Validar eventos
    console.print("[bold]▸ Eventos web[/bold]")
    df_evt, rep_evt = validar_eventos(df_evt_raw, user_ids_validos)
    _mostrar_reporte("Reglas — Eventos", rep_evt,
                     len(df_evt_raw), len(df_evt))

    # Guardar en Silver (Parquet particionado por year/month)
    path_txn = guardar_silver(df_txn, "transacciones", partition_cols=["year", "month"])
    path_evt = guardar_silver(df_evt, "eventos",       partition_cols=["year", "month"])

    console.print(f"  [green]✓ Silver transacciones:[/green] {path_txn}")
    console.print(f"  [green]✓ Silver eventos:[/green]        {path_evt}")

    # Estadísticas para el reporte
    stats_txn = {
        "filas_entrada": len(df_txn_raw),
        "filas_salidas": len(df_txn),
        "tasa_rechazo_pct": round((len(df_txn_raw) - len(df_txn)) / max(len(df_txn_raw), 1) * 100, 2),
        "amount_min":  float(df_txn["amount"].min()),
        "amount_max":  float(df_txn["amount"].max()),
        "amount_mean": float(df_txn["amount"].mean()),
    }
    stats_evt = {
        "filas_entrada": len(df_evt_raw),
        "filas_salidas": len(df_evt),
        "tasa_rechazo_pct": round((len(df_evt_raw) - len(df_evt)) / max(len(df_evt_raw), 1) * 100, 2),
        "duration_mean_sec": float(df_evt["duration_sec"].mean()),
    }

    guardar_reporte_calidad(rep_txn, rep_evt, stats_txn, stats_evt)

    # Linaje
    registrar_evento(
        origen="bronze/transacciones.parquet",
        transformacion="validacion_calidad_R01-R08",
        destino=path_txn,
        script="pipeline/calidad.py",
        filas_entrada=len(df_txn_raw),
        filas_salida=len(df_txn),
        notas="8 reglas aplicadas; particionado por year/month",
    )
    registrar_evento(
        origen="bronze/eventos.parquet",
        transformacion="validacion_calidad_R01-R07",
        destino=path_evt,
        script="pipeline/calidad.py",
        filas_entrada=len(df_evt_raw),
        filas_salida=len(df_evt),
        notas="7 reglas aplicadas; particionado por year/month",
    )

    return {"transacciones": df_txn, "eventos": df_evt}
