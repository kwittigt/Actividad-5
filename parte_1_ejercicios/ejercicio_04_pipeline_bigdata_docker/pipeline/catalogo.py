"""
pipeline/catalogo.py
Genera el catálogo de datos (metadata/catalogo.json) con:
  campo, tipo, descripción, fuente, obligatoriedad, regla asociada.
"""
import json
import os
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table

console = Console()
METADATA_DIR = "metadata"


CATALOGO = {
    "version": "1.0.0",
    "descripcion": "Catálogo de datos — Pipeline E-commerce INFB6074",
    "fuentes": [
        {
            "nombre": "transacciones",
            "archivo": "data/seeds/transacciones.csv",
            "zona_bronze": "bronze/transacciones.parquet",
            "zona_silver": "silver/transacciones/",
            "formato_origen": "CSV",
            "descripcion": "Registro de ventas del e-commerce. Una fila por transacción.",
            "campos": [
                {
                    "campo": "transaction_id",
                    "tipo": "string",
                    "descripcion": "Identificador único de la transacción",
                    "fuente": "sistema_pos",
                    "obligatorio": True,
                    "clave_primaria": True,
                    "patron": "TXN-XXXXXX",
                    "reglas": ["R01 (no nulo)", "R02 (sin duplicados)", "R07 (formato TXN-XXXXXX)"],
                },
                {
                    "campo": "user_id",
                    "tipo": "string",
                    "descripcion": "Identificador del usuario que realizó la compra",
                    "fuente": "sistema_usuarios",
                    "obligatorio": True,
                    "patron": "USR-XXXX",
                    "reglas": ["R01 (no nulo)"],
                },
                {
                    "campo": "product_id",
                    "tipo": "string",
                    "descripcion": "Identificador del producto comprado",
                    "fuente": "catalogo_productos",
                    "obligatorio": True,
                    "patron": "PRD-XXXX",
                    "reglas": ["R01 (no nulo)"],
                },
                {
                    "campo": "category",
                    "tipo": "string (enum)",
                    "descripcion": "Categoría del producto",
                    "fuente": "catalogo_productos",
                    "obligatorio": True,
                    "valores_permitidos": ["Electrónica", "Ropa", "Hogar", "Deportes", "Libros", "Juguetes"],
                    "reglas": ["R04 (categoría permitida)"],
                },
                {
                    "campo": "amount",
                    "tipo": "float",
                    "descripcion": "Monto total de la transacción en USD",
                    "fuente": "sistema_pos",
                    "obligatorio": True,
                    "rango": "> 0",
                    "reglas": ["R01 (no nulo)", "R03a (amount > 0)", "R08 (sin outliers extremos)"],
                },
                {
                    "campo": "quantity",
                    "tipo": "integer",
                    "descripcion": "Cantidad de unidades compradas",
                    "fuente": "sistema_pos",
                    "obligatorio": True,
                    "rango": ">= 1",
                    "reglas": ["R03b (quantity >= 1)"],
                },
                {
                    "campo": "date",
                    "tipo": "datetime",
                    "descripcion": "Fecha y hora de la transacción (UTC)",
                    "fuente": "sistema_pos",
                    "obligatorio": True,
                    "reglas": ["R01 (no nulo)", "R05 (no fecha futura)"],
                },
                {
                    "campo": "payment_method",
                    "tipo": "string (enum)",
                    "descripcion": "Método de pago utilizado",
                    "fuente": "sistema_pagos",
                    "obligatorio": True,
                    "valores_permitidos": ["tarjeta_credito", "tarjeta_debito", "transferencia",
                                           "efectivo", "billetera_digital"],
                    "reglas": ["R04b (método permitido)"],
                },
                {
                    "campo": "status",
                    "tipo": "string (enum)",
                    "descripcion": "Estado de la transacción",
                    "fuente": "sistema_pos",
                    "obligatorio": True,
                    "valores_permitidos": ["completada", "pendiente", "cancelada", "reembolsada"],
                    "reglas": [],
                },
                {
                    "campo": "country",
                    "tipo": "string (ISO 3166-1 alpha-2)",
                    "descripcion": "País de origen de la transacción",
                    "fuente": "sistema_pos",
                    "obligatorio": True,
                    "valores_permitidos": ["CL", "AR", "MX", "CO", "PE", "BR"],
                    "reglas": ["R01 (no nulo)"],
                },
            ],
        },
        {
            "nombre": "eventos",
            "archivo": "data/seeds/eventos.jsonl",
            "zona_bronze": "bronze/eventos.parquet",
            "zona_silver": "silver/eventos/",
            "formato_origen": "JSONL",
            "descripcion": "Eventos de clickstream / comportamiento web de usuarios.",
            "campos": [
                {
                    "campo": "event_id",
                    "tipo": "string",
                    "descripcion": "Identificador único del evento",
                    "fuente": "analytics_web",
                    "obligatorio": True,
                    "clave_primaria": True,
                    "patron": "EVT-XXXXXXX",
                    "reglas": ["R01 (no nulo)", "R02 (sin duplicados)", "R07 (formato EVT-XXXXXXX)"],
                },
                {
                    "campo": "user_id",
                    "tipo": "string",
                    "descripcion": "Usuario que generó el evento (FK a transacciones.user_id)",
                    "fuente": "analytics_web",
                    "obligatorio": True,
                    "reglas": ["R01 (no nulo)", "R06 (integridad referencial con transacciones)"],
                },
                {
                    "campo": "session_id",
                    "tipo": "string",
                    "descripcion": "Identificador de la sesión web",
                    "fuente": "analytics_web",
                    "obligatorio": True,
                    "reglas": ["R01 (no nulo)"],
                },
                {
                    "campo": "event_type",
                    "tipo": "string (enum)",
                    "descripcion": "Tipo de interacción registrada",
                    "fuente": "analytics_web",
                    "obligatorio": True,
                    "valores_permitidos": ["page_view", "click", "add_to_cart",
                                           "purchase", "search", "logout"],
                    "reglas": ["R04a (tipo de evento permitido)"],
                },
                {
                    "campo": "page",
                    "tipo": "string",
                    "descripcion": "URL relativa de la página donde ocurrió el evento",
                    "fuente": "analytics_web",
                    "obligatorio": False,
                    "reglas": [],
                },
                {
                    "campo": "timestamp",
                    "tipo": "datetime",
                    "descripcion": "Marca de tiempo UTC del evento",
                    "fuente": "analytics_web",
                    "obligatorio": True,
                    "reglas": ["R01 (no nulo)", "R05 (no timestamp futuro)"],
                },
                {
                    "campo": "device",
                    "tipo": "string (enum)",
                    "descripcion": "Tipo de dispositivo desde el que se generó el evento",
                    "fuente": "analytics_web",
                    "obligatorio": True,
                    "valores_permitidos": ["mobile", "desktop", "tablet"],
                    "reglas": ["R04b (dispositivo permitido)"],
                },
                {
                    "campo": "browser",
                    "tipo": "string",
                    "descripcion": "Navegador web utilizado",
                    "fuente": "analytics_web",
                    "obligatorio": False,
                    "reglas": [],
                },
                {
                    "campo": "duration_sec",
                    "tipo": "float",
                    "descripcion": "Duración en segundos de la interacción",
                    "fuente": "analytics_web",
                    "obligatorio": False,
                    "rango": ">= 0",
                    "reglas": ["R03 (duration_sec >= 0)"],
                },
            ],
        },
    ],
    "tablas_gold": [
        {
            "nombre": "ventas_categoria_mes",
            "ruta": "gold/ventas_categoria_mes/",
            "descripcion": "Ingresos, unidades y transacciones agregadas por categoría, país y mes.",
            "particionado_por": ["year", "month"],
            "origen": ["silver/transacciones"],
        },
        {
            "nombre": "perfil_usuarios",
            "ruta": "gold/perfil_usuarios.parquet",
            "descripcion": "Perfil de usuario con métricas de compra y comportamiento web.",
            "particionado_por": None,
            "origen": ["silver/transacciones", "silver/eventos"],
        },
        {
            "nombre": "conversion_funnel",
            "ruta": "gold/conversion_funnel.parquet",
            "descripcion": "Embudo de conversión desde page_view hasta purchase.",
            "particionado_por": None,
            "origen": ["silver/eventos"],
        },
    ],
}


RESUMEN_REGLAS = [
    {"id": "R01", "nombre": "Nulos obligatorios",       "descripcion": "Los campos marcados como obligatorios no pueden contener nulos.",           "accion": "Eliminar fila"},
    {"id": "R02", "nombre": "Clave primaria duplicada", "descripcion": "Cada clave primaria debe ser única en el dataset.",                          "accion": "Eliminar duplicados (keep=first)"},
    {"id": "R03", "nombre": "Rangos inválidos",         "descripcion": "amount > 0, quantity >= 1, duration_sec >= 0.",                              "accion": "Eliminar fila"},
    {"id": "R04", "nombre": "Categorías no permitidas", "descripcion": "Los campos enum solo aceptan valores del vocabulario controlado.",            "accion": "Eliminar fila"},
    {"id": "R05", "nombre": "Fechas futuras",           "descripcion": "date/timestamp no puede superar la fecha/hora de ejecución del pipeline.",   "accion": "Eliminar fila"},
    {"id": "R06", "nombre": "Integridad referencial",   "descripcion": "user_id en eventos debe existir en el conjunto de user_ids de transacciones.", "accion": "Eliminar fila"},
    {"id": "R07", "nombre": "Formato de identificador", "descripcion": "transaction_id ≡ TXN-XXXXXX; event_id ≡ EVT-XXXXXXX.",                       "accion": "Eliminar fila"},
    {"id": "R08", "nombre": "Outliers estadísticos",    "descripcion": "amount por encima de Q3 + 3·IQR se marca como outlier extremo.",             "accion": "Registrar (no eliminar en Silver)"},
]


def generar_catalogo() -> None:
    console.rule("[bold white]CATÁLOGO DE DATOS")
    os.makedirs(METADATA_DIR, exist_ok=True)

    catalogo_completo = {
        **CATALOGO,
        "reglas_calidad": RESUMEN_REGLAS,
        "generado_utc": datetime.now(timezone.utc).isoformat(),
    }

    path = os.path.join(METADATA_DIR, "catalogo.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(catalogo_completo, f, ensure_ascii=False, indent=2)

    # Mostrar tabla de reglas
    tabla = Table(title="Catálogo — Reglas de Calidad", show_lines=True)
    tabla.add_column("ID",    style="cyan", width=6)
    tabla.add_column("Regla", width=25)
    tabla.add_column("Descripción", overflow="fold", width=55)
    tabla.add_column("Acción", width=30)

    for r in RESUMEN_REGLAS:
        tabla.add_row(r["id"], r["nombre"], r["descripcion"], r["accion"])
    console.print(tabla)
    console.print(f"\n  [green]✓ Catálogo guardado:[/green] {path}\n")
