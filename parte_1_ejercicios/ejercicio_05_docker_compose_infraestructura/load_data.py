#!/usr/bin/env python3
"""
load_data.py
============
Genera un dataset sintético de ventas y lo carga en PostgreSQL.

Ejecutar desde JupyterLab o desde el contenedor:
    python /home/jovyan/scripts/load_data.py

Variables de entorno requeridas (definidas en docker-compose.yml):
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""

import os
import random
import time
from datetime import date, timedelta

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

# ── Configuración ──────────────────────────────────────────────────────────────
fake = Faker("es_CL")
random.seed(42)

DB = {
    "host":     os.getenv("DB_HOST",     "postgres"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "user":     os.getenv("DB_USER",     "dsuser"),
    "password": os.getenv("DB_PASSWORD", "dspassword"),
    "dbname":   os.getenv("DB_NAME",     "dsdb"),
}

CATEGORIAS = ["Electrónica", "Ropa", "Alimentos", "Hogar", "Deportes"]
REGIONES   = ["RM", "Valparaíso", "Biobío", "Araucanía", "Los Lagos", "Antofagasta"]
CANALES    = ["online", "tienda", "b2b"]

PRODUCTOS = [
    ("Laptop Pro 15",          "Electrónica", 899_990),
    ("Auriculares Bluetooth",  "Electrónica",  49_990),
    ("Smartwatch X200",        "Electrónica", 149_990),
    ("Tablet 10 pulgadas",     "Electrónica", 299_990),
    ("Polera de algodón",      "Ropa",          12_990),
    ("Zapatillas Running",     "Deportes",      89_990),
    ("Chaqueta impermeable",   "Ropa",          59_990),
    ("Arroz integral 5 kg",    "Alimentos",      5_490),
    ("Aceite de oliva 1 L",    "Alimentos",      7_990),
    ("Silla ergonómica",       "Hogar",        199_990),
    ("Lámpara LED escritorio", "Hogar",         29_990),
    ("Bicicleta de montaña",   "Deportes",     499_990),
    ("Mochila táctica 30 L",   "Deportes",      69_990),
    ("Hervidor eléctrico",     "Hogar",         24_990),
    ("Jeans slim fit",         "Ropa",          39_990),
]

N_TRANSACCIONES = 2_000  # registros a generar
FECHA_INICIO    = date(2024, 1, 1)
FECHA_FIN       = date(2024, 12, 31)


# ── Helpers ────────────────────────────────────────────────────────────────────

def fecha_aleatoria(inicio: date, fin: date) -> date:
    delta = (fin - inicio).days
    return inicio + timedelta(days=random.randint(0, delta))


def esperar_postgres(reintentos: int = 10, espera: int = 3) -> psycopg2.extensions.connection:
    """Reintenta la conexión hasta que PostgreSQL esté listo."""
    for intento in range(1, reintentos + 1):
        try:
            conn = psycopg2.connect(**DB)
            print(f"✔  Conexión a PostgreSQL exitosa (intento {intento}).")
            return conn
        except psycopg2.OperationalError as e:
            print(f"⏳  PostgreSQL no disponible aún ({intento}/{reintentos}): {e}")
            time.sleep(espera)
    raise RuntimeError("No se pudo conectar a PostgreSQL después de varios intentos.")


# ── Carga de productos ─────────────────────────────────────────────────────────

def cargar_productos(cur) -> dict[str, int]:
    """Inserta los productos base y retorna un mapa nombre→id."""
    cur.execute("SELECT COUNT(*) FROM ventas.productos;")
    if cur.fetchone()[0] > 0:
        print("ℹ  Productos ya existentes; omitiendo inserción.")
        cur.execute("SELECT nombre, id FROM ventas.productos;")
        return {row[0]: row[1] for row in cur.fetchall()}

    rows = [(nombre, cat, precio) for nombre, cat, precio in PRODUCTOS]
    execute_values(
        cur,
        "INSERT INTO ventas.productos (nombre, categoria, precio_unitario) VALUES %s RETURNING nombre, id;",
        rows,
    )
    resultado = {row[0]: row[1] for row in cur.fetchall()}
    print(f"✔  {len(resultado)} productos insertados.")
    return resultado


# ── Generación y carga de transacciones ───────────────────────────────────────

def generar_transacciones(producto_ids: dict[str, int]) -> list[tuple]:
    """Genera N_TRANSACCIONES filas sintéticas."""
    nombres   = list(producto_ids.keys())
    precios   = {n: p for n, _, p in PRODUCTOS}
    registros = []

    for _ in range(N_TRANSACCIONES):
        nombre      = random.choice(nombres)
        producto_id = producto_ids[nombre]
        cantidad    = random.randint(1, 10)
        precio      = precios[nombre]
        descuento   = random.choice([0, 0.05, 0.10, 0.15])
        total       = round(cantidad * precio * (1 - descuento), 2)
        fecha       = fecha_aleatoria(FECHA_INICIO, FECHA_FIN)
        region      = random.choice(REGIONES)
        canal       = random.choices(CANALES, weights=[0.5, 0.35, 0.15])[0]
        registros.append((producto_id, cantidad, fecha, region, canal, total))

    return registros


def cargar_transacciones(cur, filas: list[tuple]) -> None:
    cur.execute("SELECT COUNT(*) FROM ventas.transacciones;")
    if cur.fetchone()[0] > 0:
        print("ℹ  Transacciones ya existentes; omitiendo inserción.")
        return

    execute_values(
        cur,
        """INSERT INTO ventas.transacciones
               (producto_id, cantidad, fecha, region, canal, total)
           VALUES %s;""",
        filas,
    )
    print(f"✔  {len(filas):,} transacciones insertadas.")


# ── Exportar CSV como evidencia de persistencia ───────────────────────────────

def exportar_csv(conn) -> None:
    df = pd.read_sql(
        """
        SELECT t.id, p.nombre, p.categoria, t.cantidad,
               t.fecha, t.region, t.canal, t.total
        FROM ventas.transacciones t
        JOIN ventas.productos p ON p.id = t.producto_id
        ORDER BY t.fecha
        LIMIT 500;
        """,
        conn,
    )
    ruta = "/home/jovyan/datasets/ventas_muestra.csv"
    df.to_csv(ruta, index=False)
    print(f"✔  CSV exportado → {ruta}  ({len(df)} filas)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  CARGA DE DATOS — Mini Infraestructura DS")
    print("=" * 55)

    conn = None
    try:
        conn = esperar_postgres()

        # Bloque transaccional para cargar datos
        with conn:
            with conn.cursor() as cur:
                producto_ids = cargar_productos(cur)
                filas = generar_transacciones(producto_ids)
                cargar_transacciones(cur, filas)

        # Operaciones post-transacción
        exportar_csv(conn)
        print("\n✅  Carga completada exitosamente.")

    except Exception as exc:
        print(f"\n❌  Error durante la operación: {exc}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
