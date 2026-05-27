#!/usr/bin/env python3
"""
query_analysis.py
=================
Ejecuta consultas analíticas sobre la base de datos PostgreSQL y
genera un reporte de resultados en /home/jovyan/datasets/reporte.txt

Diseñado para ejecutarse DESPUÉS de load_data.py.

Uso:
    python /home/jovyan/scripts/query_analysis.py
"""

import os
import textwrap
from datetime import datetime
from io import StringIO

import pandas as pd
import psycopg2

# ── Conexión ───────────────────────────────────────────────────────────────────
DB = {
    "host":     os.getenv("DB_HOST",     "postgres"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "user":     os.getenv("DB_USER",     "dsuser"),
    "password": os.getenv("DB_PASSWORD", "dspassword"),
    "dbname":   os.getenv("DB_NAME",     "dsdb"),
}

OUTPUT_PATH = "/home/jovyan/datasets/reporte.txt"

# ── Consultas ──────────────────────────────────────────────────────────────────

QUERIES = {
    "resumen_general": """
        SELECT
            COUNT(*)                                    AS total_transacciones,
            SUM(cantidad)                               AS unidades_totales,
            ROUND(SUM(total)::NUMERIC, 0)               AS ingresos_totales_clp,
            ROUND(AVG(total)::NUMERIC, 0)               AS ticket_promedio_clp,
            MIN(fecha)                                  AS primera_venta,
            MAX(fecha)                                  AS ultima_venta
        FROM ventas.transacciones;
    """,

    "ventas_por_categoria": """
        SELECT
            p.categoria,
            COUNT(*)                             AS num_ventas,
            SUM(t.cantidad)                      AS unidades,
            ROUND(SUM(t.total)::NUMERIC, 0)      AS ingresos_clp,
            ROUND(
                100.0 * SUM(t.total) /
                SUM(SUM(t.total)) OVER ()
            , 1)                                 AS pct_ingresos
        FROM ventas.transacciones t
        JOIN ventas.productos p ON p.id = t.producto_id
        GROUP BY p.categoria
        ORDER BY ingresos_clp DESC;
    """,

    "ventas_por_region": """
        SELECT
            region,
            COUNT(*)                             AS num_ventas,
            ROUND(SUM(total)::NUMERIC, 0)        AS ingresos_clp,
            ROUND(AVG(total)::NUMERIC, 0)        AS ticket_promedio_clp
        FROM ventas.transacciones
        GROUP BY region
        ORDER BY ingresos_clp DESC;
    """,

    "ventas_por_canal": """
        SELECT
            canal,
            COUNT(*)                             AS num_ventas,
            ROUND(SUM(total)::NUMERIC, 0)        AS ingresos_clp,
            ROUND(
                100.0 * COUNT(*) / SUM(COUNT(*)) OVER ()
            , 1)                                 AS pct_ventas
        FROM ventas.transacciones
        GROUP BY canal
        ORDER BY ingresos_clp DESC;
    """,

    "top5_productos": """
        SELECT
            p.nombre,
            p.categoria,
            COUNT(*)                         AS num_ventas,
            SUM(t.cantidad)                  AS unidades,
            ROUND(SUM(t.total)::NUMERIC, 0)  AS ingresos_clp
        FROM ventas.transacciones t
        JOIN ventas.productos p ON p.id = t.producto_id
        GROUP BY p.nombre, p.categoria
        ORDER BY ingresos_clp DESC
        LIMIT 5;
    """,

    "tendencia_mensual": """
        SELECT
            TO_CHAR(fecha, 'YYYY-MM')        AS mes,
            COUNT(*)                          AS num_ventas,
            ROUND(SUM(total)::NUMERIC, 0)     AS ingresos_clp
        FROM ventas.transacciones
        GROUP BY mes
        ORDER BY mes;
    """,

    "mejor_dia_semana": """
        SELECT
            TO_CHAR(fecha, 'Day')             AS dia_semana,
            EXTRACT(DOW FROM fecha)::INT      AS dow,
            COUNT(*)                          AS num_ventas,
            ROUND(AVG(total)::NUMERIC, 0)     AS ticket_promedio
        FROM ventas.transacciones
        GROUP BY dia_semana, dow
        ORDER BY dow;
    """,
}

# ── Utilidades ─────────────────────────────────────────────────────────────────

SEP  = "─" * 70
SEP2 = "═" * 70

def seccion(titulo: str) -> str:
    return f"\n{SEP2}\n  {titulo.upper()}\n{SEP2}\n"


def df_to_str(df: pd.DataFrame) -> str:
    return df.to_string(index=False)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Conectando a PostgreSQL...")
    conn = None
    try:
        conn = psycopg2.connect(**DB)
        buffer = StringIO()

        header = textwrap.dedent(f"""
        {SEP2}
          REPORTE DE ANÁLISIS DE VENTAS
          Generado : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
          Fuente   : PostgreSQL → dsdb / ventas
        {SEP2}
        """)
        buffer.write(header)
        print(header)

        titulos = {
            "resumen_general":      "1. Resumen General",
            "ventas_por_categoria": "2. Ingresos por Categoría",
            "ventas_por_region":    "3. Ventas por Región",
            "ventas_por_canal":     "4. Distribución por Canal de Venta",
            "top5_productos":       "5. Top 5 Productos por Ingresos",
            "tendencia_mensual":    "6. Tendencia Mensual de Ingresos",
            "mejor_dia_semana":     "7. Ventas Promedio por Día de Semana",
        }

        for key, titulo in titulos.items():
            df = pd.read_sql(QUERIES[key], conn)
            bloque = seccion(titulo) + df_to_str(df) + "\n"
            buffer.write(bloque)
            print(bloque)

        # Análisis adicional en Pandas: variabilidad por región-canal
        df_pivot = pd.read_sql(
            """
            SELECT region, canal, ROUND(SUM(total)::NUMERIC, 0) AS ingresos
            FROM ventas.transacciones
            GROUP BY region, canal
            ORDER BY region, canal;
            """,
            conn,
        )
        pivot = df_pivot.pivot(index="region", columns="canal", values="ingresos").fillna(0)
        pivot["TOTAL"] = pivot.sum(axis=1)
        bloque = seccion("8. Pivot: Ingresos por Región × Canal (CLP)") + pivot.to_string() + "\n"
        buffer.write(bloque)
        print(bloque)

        # Guardar reporte en volumen persistente
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(buffer.getvalue())

        print(f"\n✅  Reporte guardado en {OUTPUT_PATH}")
        print("    (el archivo persiste en el volumen 'datasets_data')\n")

    except (psycopg2.Error, Exception) as exc:
        print(f"\n❌  Error durante el análisis: {exc}")
        raise
    finally:
        if conn:
            conn.close()
            print("... Conexión a PostgreSQL cerrada.")


if __name__ == "__main__":
    main()
