# Pipeline Big Data Local — INFB6074
## E-commerce Analytics: Bronze → Silver → Gold

Pipeline reproducible de datos para análisis de ventas e-commerce, implementado con Python 3.11, Docker y Parquet columnar.

---

## Escenario

Se simula una plataforma de comercio electrónico latinoamericana con operaciones en Chile, Argentina, México, Colombia, Perú y Brasil. Dos fuentes de datos alimentan el sistema:

| Fuente | Formato | Registros | Descripción |
|--------|---------|-----------|-------------|
| `transacciones.csv` | CSV | 5 000 | Ventas: monto, producto, categoría, método de pago, estado |
| `eventos.jsonl` | JSONL | 8 000 | Clickstream: tipo de evento, sesión, dispositivo, duración |

---

## Estructura del proyecto

```
.
├── Dockerfile                  # Imagen reproducible Python 3.11.9
├── requirements.txt            # Dependencias con versiones fijas
├── README.md
│
├── data/
│   ├── generador.py            # Genera datos sintéticos con errores intencionales
│   └── seeds/
│       ├── transacciones.csv
│       └── eventos.jsonl
│
├── pipeline/
│   ├── main.py                 # Orquestador principal
│   ├── ingesta.py              # Zona Bronze
│   ├── calidad.py              # Zona Silver + 8 reglas de calidad
│   ├── transformacion.py       # Zona Gold (3 tablas analíticas)
│   ├── consultas.py            # 5 consultas DuckDB / Pandas / Polars
│   ├── catalogo.py             # Generador del catálogo de datos
│   └── linaje.py               # Registro de linaje JSONL
│
├── bronze/                     # Datos crudos (Parquet sin transformar)
├── silver/                     # Datos limpios, particionados por year/month
├── gold/                       # Tablas analíticas agregadas
├── metadata/
│   ├── catalogo.json           # Catálogo de campos y reglas
│   └── linaje.jsonl            # Registro de cada transformación
└── metrics/
    ├── reporte_calidad.json    # Estadísticas por regla
    ├── dashboard_analitico.png # 6 visualizaciones analíticas
    └── query_*.parquet         # Resultados de consultas
```

---

## Ejecución

### Con Docker (reproducible)

```bash
# Construir la imagen con versión fija de Python y dependencias
docker build -t infb6074-pipeline .

# Ejecutar el pipeline completo (monta el directorio actual)
docker run --rm -v "$(pwd)":/work infb6074-pipeline
```

### Sin Docker (local)

```bash
pip install -r requirements.txt
python pipeline/main.py
```

---

## Zonas del pipeline

### Bronze — Ingesta cruda
- Lee `transacciones.csv` y `eventos.jsonl` sin transformar.
- Agrega metadatos: `_ingested_at`, `_source_file`.
- Guarda en `bronze/` como Parquet plano.
- Conserva copia raw en `bronze/raw/` para trazabilidad.

### Silver — Calidad y limpieza

Se aplican **8 reglas de calidad**:

| ID | Regla | Acción |
|----|-------|--------|
| R01 | Nulos en campos obligatorios | Eliminar fila |
| R02 | Duplicados en clave primaria | Eliminar duplicados (keep=first) |
| R03 | Rangos inválidos (amount > 0, quantity ≥ 1, duration_sec ≥ 0) | Eliminar fila |
| R04 | Categorías / métodos de pago / tipos de evento no permitidos | Eliminar fila |
| R05 | Fechas o timestamps futuros | Eliminar fila |
| R06 | Integridad referencial: user_id en eventos ∉ user_ids en transacciones | Eliminar fila |
| R07 | Formato de identificador (TXN-XXXXXX / EVT-XXXXXXX) | Eliminar fila |
| R08 | Outliers estadísticos en amount (> Q3 + 3·IQR) | Solo registrar |

Los datos limpios se guardan **particionados por `year` y `month`** en `silver/`.

### Gold — Tablas analíticas

| Tabla | Descripción | Partición |
|-------|-------------|-----------|
| `ventas_categoria_mes` | Ingresos, unidades y transacciones por categoría, país y mes | year / month |
| `perfil_usuarios` | Perfil RFM-like: compras, gasto, eventos, sesiones por usuario | — |
| `conversion_funnel` | Embudo de conversión: page_view → search → click → add_to_cart → purchase | — |

---

## Consultas analíticas

| # | Motor | Consulta |
|---|-------|----------|
| 1 | **DuckDB** | Top categorías por ingresos totales |
| 2 | **DuckDB** | Serie temporal mensual con ingresos acumulados (window function) |
| 3 | **Pandas** | Segmentación RFM (Recency, Frequency, Monetary) con quintiles |
| 4 | **Polars** | Comportamiento por dispositivo y navegador (lazy evaluation) |
| 5 | **DuckDB** | Análisis geográfico con % de participación por país |

---

## Catálogo de datos

El archivo `metadata/catalogo.json` documenta cada campo con:

```json
{
  "campo": "amount",
  "tipo": "float",
  "descripcion": "Monto total de la transacción en USD",
  "fuente": "sistema_pos",
  "obligatorio": true,
  "rango": "> 0",
  "reglas": ["R01 (no nulo)", "R03a (amount > 0)", "R08 (sin outliers extremos)"]
}
```

---

## Linaje de datos

El archivo `metadata/linaje.jsonl` registra cada transformación:

```json
{
  "timestamp_utc": "2024-01-01T00:00:00+00:00",
  "origen": "bronze/transacciones.parquet",
  "transformacion": "validacion_calidad_R01-R08",
  "destino": "silver/transacciones",
  "script_responsable": "pipeline/calidad.py",
  "filas_entrada": 5000,
  "filas_salida": 4591,
  "filas_eliminadas": 409,
  "notas": "8 reglas aplicadas; particionado por year/month"
}
```

---

## Docker y reproducibilidad

Docker aporta tres garantías fundamentales a este pipeline:

### 1. Reproducibilidad
El `Dockerfile` fija `python:3.11.9-slim` y el `requirements.txt` fija cada dependencia con versión exacta (`pandas==2.2.2`, `duckdb==1.0.0`, etc.). Esto garantiza que el pipeline produce **exactamente el mismo resultado** en cualquier máquina, en cualquier fecha.

### 2. Aislamiento de dependencias
El contenedor tiene su propio entorno Python aislado del sistema operativo del host. No hay conflictos entre versiones de librerías de distintos proyectos.

### 3. Comparación controlada
Al cambiar las reglas de calidad o la lógica de transformación, se puede construir una nueva imagen (`v2.0`) y correrla en paralelo con la anterior sobre los mismos datos, comparando resultados de forma controlada sin alterar el entorno de producción.

---

## Métricas de ejecución (ejemplo)

| Dataset | Filas entrada | Filas limpias | Tasa de rechazo |
|---------|-------------|---------------|-----------------|
| Transacciones | 5 000 | ~4 591 | ~8.2% |
| Eventos | 8 000 | ~7 316 | ~8.5% |

---

## Dependencias principales

```
pandas==2.2.2       # ETL y operaciones vectorizadas
pyarrow==16.1.0     # Backend Parquet + formato Arrow
duckdb==1.0.0       # SQL analítico sobre Parquet directamente
polars==0.20.31     # Procesamiento columnar con lazy evaluation
matplotlib==3.9.0   # Visualizaciones
rich==13.7.1        # Output formateado en consola
```
