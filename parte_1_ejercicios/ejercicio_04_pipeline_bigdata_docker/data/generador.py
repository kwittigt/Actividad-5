"""
data/generador.py
Genera datos sintéticos para el pipeline:
  - transacciones.csv  → ventas de e-commerce
  - eventos.jsonl      → eventos web / clickstream
Incluye intencionalmente errores para probar las reglas de calidad.
"""
import csv
import json
import random
import os
from datetime import datetime, timedelta

random.seed(42)

# ── Constantes ───────────────────────────────────────────────────────────────
CATEGORIAS      = ["Electrónica", "Ropa", "Hogar", "Deportes", "Libros", "Juguetes"]
METODOS_PAGO    = ["tarjeta_credito", "tarjeta_debito", "transferencia", "efectivo", "billetera_digital"]
ESTADOS         = ["completada", "pendiente", "cancelada", "reembolsada"]
PAISES          = ["CL", "AR", "MX", "CO", "PE", "BR"]
TIPOS_EVENTO    = ["page_view", "click", "add_to_cart", "purchase", "search", "logout"]
DISPOSITIVOS    = ["mobile", "desktop", "tablet"]
NAVEGADORES     = ["Chrome", "Firefox", "Safari", "Edge"]

N_TRANSACCIONES = 5_000
N_EVENTOS       = 8_000
N_USUARIOS      = 500
N_PRODUCTOS     = 200

BASE_DATE = datetime(2024, 1, 1)
FUTURE_DATE = datetime(2026, 12, 31)  # fecha futura intencional para regla de calidad


def random_date(start: datetime, days: int = 365) -> str:
    return (start + timedelta(days=random.randint(0, days))).strftime("%Y-%m-%d %H:%M:%S")


def generar_transacciones(n: int) -> list[dict]:
    rows = []
    used_ids = set()

    for i in range(n):
        txn_id = f"TXN-{i:06d}"

        # Regla 2: ~1% duplicados intencionales
        if random.random() < 0.01 and used_ids:
            txn_id = random.choice(list(used_ids))
        else:
            used_ids.add(txn_id)

        user_id = f"USR-{random.randint(1, N_USUARIOS):04d}" if random.random() > 0.02 else None  # Regla 1: nulos
        product_id = f"PRD-{random.randint(1, N_PRODUCTOS):04d}"
        categoria = random.choice(CATEGORIAS) if random.random() > 0.015 else "Categoría_Inválida"  # Regla 4
        amount = round(random.uniform(1.0, 2000.0), 2)

        # Regla 3: rangos inválidos (~2% negativos)
        if random.random() < 0.02:
            amount = round(random.uniform(-500, -1), 2)

        quantity = random.randint(1, 10)
        if random.random() < 0.01:
            quantity = -random.randint(1, 5)  # cantidad negativa

        # Regla 5: fechas futuras (~1%)
        fecha = random_date(FUTURE_DATE, 200) if random.random() < 0.01 else random_date(BASE_DATE, 365)

        metodo = random.choice(METODOS_PAGO) if random.random() > 0.015 else "criptomoneda"  # Regla 4
        estado = random.choice(ESTADOS)
        pais = random.choice(PAISES) if random.random() > 0.01 else None  # Regla 1

        rows.append({
            "transaction_id": txn_id,
            "user_id": user_id,
            "product_id": product_id,
            "category": categoria,
            "amount": amount,
            "quantity": quantity,
            "date": fecha,
            "payment_method": metodo,
            "status": estado,
            "country": pais,
        })
    return rows


def generar_eventos(n: int) -> list[dict]:
    events = []
    used_event_ids = set()

    for i in range(n):
        event_id = f"EVT-{i:07d}"

        # Regla 2: ~0.5% duplicados
        if random.random() < 0.005 and used_event_ids:
            event_id = random.choice(list(used_event_ids))
        else:
            used_event_ids.add(event_id)

        user_id = f"USR-{random.randint(1, N_USUARIOS):04d}" if random.random() > 0.03 else None
        session_id = f"SES-{random.randint(1, 2000):05d}"
        event_type = random.choice(TIPOS_EVENTO) if random.random() > 0.01 else "invalid_event"  # Regla 4
        page = f"/page-{random.randint(1, 50)}" if random.random() > 0.02 else None
        timestamp = random_date(FUTURE_DATE, 100) if random.random() < 0.008 else random_date(BASE_DATE, 365)
        device = random.choice(DISPOSITIVOS)
        browser = random.choice(NAVEGADORES)
        duration_sec = round(random.uniform(0.5, 600.0), 2)

        # Regla 3: duración negativa
        if random.random() < 0.015:
            duration_sec = round(random.uniform(-60, -0.1), 2)

        # Regla 6: referential integrity — ~2% de user_ids que NO existen en transacciones
        if random.random() < 0.02:
            user_id = f"USR-{random.randint(9000, 9999):04d}"

        events.append({
            "event_id": event_id,
            "user_id": user_id,
            "session_id": session_id,
            "event_type": event_type,
            "page": page,
            "timestamp": timestamp,
            "device": device,
            "browser": browser,
            "duration_sec": duration_sec,
        })
    return events


def guardar_csv(rows: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ CSV generado: {path}  ({len(rows):,} filas)")


def guardar_jsonl(records: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  ✓ JSONL generado: {path}  ({len(records):,} registros)")


if __name__ == "__main__":
    print("\n🔧 Generando datos sintéticos de e-commerce...\n")
    base = os.path.join(os.path.dirname(__file__), "seeds")

    transacciones = generar_transacciones(N_TRANSACCIONES)
    eventos = generar_eventos(N_EVENTOS)

    guardar_csv(transacciones, os.path.join(base, "transacciones.csv"))
    guardar_jsonl(eventos, os.path.join(base, "eventos.jsonl"))
    print("\n  Datos listos en data/seeds/\n")
