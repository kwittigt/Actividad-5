# Pipeline Big Data local con Docker

Este ejercicio implementa un pipeline de datos para un caso de e-commerce. La idea es simular dos fuentes de informacion, procesarlas por capas y dejar resultados listos para analisis: datos crudos, datos limpios, tablas agregadas, metricas de calidad, consultas y un pequeno registro de linaje.

El proyecto esta pensado para poder ejecutarse localmente con Python o dentro de Docker, manteniendo las mismas versiones de librerias.

## Que hace el pipeline

El flujo completo se ejecuta desde `pipeline/main.py` y sigue estos pasos:

1. Genera datos sinteticos de transacciones y eventos web.
2. Carga las fuentes originales en la zona `bronze/`.
3. Aplica reglas de calidad y guarda datos limpios en `silver/`.
4. Construye tablas analiticas en `gold/`.
5. Ejecuta consultas con DuckDB, Pandas y Polars.
6. Genera reportes, dashboard, catalogo de datos y linaje.

Las fuentes simuladas son:

| Archivo | Formato | Descripcion |
| --- | --- | --- |
| `data/seeds/transacciones.csv` | CSV | Ventas del e-commerce: usuario, producto, categoria, monto, estado, pais y metodo de pago. |
| `data/seeds/eventos.jsonl` | JSONL | Eventos de navegacion: sesiones, tipo de evento, dispositivo, navegador y duracion. |

## Estructura del proyecto

```text
.
|-- Dockerfile
|-- requirements.txt
|-- README.md
|-- data/
|   |-- generador.py
|   `-- seeds/
|       |-- transacciones.csv
|       `-- eventos.jsonl
|-- pipeline/
|   |-- main.py
|   |-- ingesta.py
|   |-- calidad.py
|   |-- transformacion.py
|   |-- consultas.py
|   |-- catalogo.py
|   `-- linaje.py
|-- bronze/
|-- silver/
|-- gold/
|-- metadata/
|-- metrics/
`-- logs/
```

En resumen:

- `data/` contiene el generador y los archivos de entrada.
- `pipeline/` contiene el codigo del proceso.
- `bronze/`, `silver/` y `gold/` son las zonas de datos.
- `metadata/` guarda el catalogo y el linaje.
- `metrics/` guarda reportes, consultas y el dashboard.
- `logs/` guarda salidas de ejecucion.

## Modulos principales

`pipeline/main.py` es el orquestador. No hace las transformaciones directamente; llama a cada modulo en orden para que el flujo sea mas facil de seguir.

`data/generador.py` crea los datos de prueba. Incluye algunos errores intencionales para que la etapa de calidad tenga casos reales que validar, como valores nulos, duplicados, rangos invalidos o fechas futuras.

`pipeline/ingesta.py` representa la capa Bronze. Lee los archivos CSV y JSONL, agrega columnas tecnicas como `_ingested_at` y `_source_file`, guarda Parquet en `bronze/` y conserva una copia raw en `bronze/raw/`.

`pipeline/calidad.py` representa la capa Silver. Convierte tipos, valida los datos y elimina registros que no cumplen reglas basicas de calidad. Tambien genera `metrics/reporte_calidad.json`.

`pipeline/transformacion.py` representa la capa Gold. A partir de los datos limpios construye tres salidas analiticas:

- `ventas_categoria_mes`: ventas agregadas por categoria, pais, anio y mes.
- `perfil_usuarios`: resumen tipo RFM por usuario.
- `conversion_funnel`: embudo de conversion por sesiones.

`pipeline/consultas.py` ejecuta consultas analiticas usando distintas herramientas. DuckDB se usa para SQL sobre Parquet, Pandas para segmentacion RFM y Polars para procesamiento columnar. Tambien genera el dashboard en `metrics/dashboard_analitico.png`.

`pipeline/catalogo.py` genera `metadata/catalogo.json`, con descripcion de campos, reglas y tablas del pipeline.

`pipeline/linaje.py` registra eventos en `metadata/linaje.jsonl`, dejando trazabilidad simple de origen, transformacion, destino, script y cantidad de filas.

## Reglas de calidad aplicadas

La etapa Silver valida principalmente:

| Regla | Que revisa | Accion |
| --- | --- | --- |
| R01 | Campos obligatorios nulos | Elimina registros invalidos |
| R02 | Claves primarias duplicadas | Conserva el primer registro |
| R03 | Rangos invalidos, como montos menores o iguales a cero | Elimina registros invalidos |
| R04 | Categorias, metodos de pago, eventos o dispositivos no permitidos | Elimina registros invalidos |
| R05 | Fechas futuras | Elimina registros invalidos |
| R06 | Usuarios de eventos que no existen en transacciones | Elimina registros invalidos |
| R07 | Formato incorrecto de identificadores | Elimina registros invalidos |
| R08 | Outliers extremos en monto | Los registra en el reporte |

## Como ejecutar

### Opcion 1: con Docker

Desde la carpeta del ejercicio:

```bash
docker build -t infb6074-pipeline .
docker run --rm -v "$(pwd)":/work infb6074-pipeline
```

Esta opcion es la mas reproducible porque usa la imagen `python:3.11.9-slim` y las versiones fijadas en `requirements.txt`.

### Opcion 2: local con Python

```bash
pip install -r requirements.txt
python pipeline/main.py
```

Tambien se puede cambiar la cantidad de datos generados:

```bash
python pipeline/main.py --transacciones 5000 --eventos 8000 --seed 42
```

## Salidas esperadas

Despues de ejecutar el pipeline deberian aparecer o actualizarse estos archivos:

| Ruta | Contenido |
| --- | --- |
| `bronze/*.parquet` | Datos crudos convertidos a Parquet. |
| `silver/` | Datos limpios particionados por `year` y `month`. |
| `gold/` | Tablas analiticas finales. |
| `metrics/reporte_calidad.json` | Resumen de reglas de calidad y filas rechazadas. |
| `metrics/query_*.parquet` | Resultados de consultas analiticas. |
| `metrics/dashboard_analitico.png` | Dashboard con graficos principales. |
| `metadata/catalogo.json` | Catalogo de datos del pipeline. |
| `metadata/linaje.jsonl` | Registro de transformaciones ejecutadas. |

Si aparecen archivos con nombre `*_historico.*`, corresponden a resultados guardados de ejecuciones anteriores.

## Dependencias usadas

Las librerias principales son:

- `pandas` y `numpy` para transformaciones de datos.
- `pyarrow` para leer y escribir Parquet.
- `duckdb` para consultas SQL directamente sobre archivos Parquet.
- `polars` para consultas columnares.
- `matplotlib` y `seaborn` para visualizaciones.
- `rich` para mostrar tablas y mensajes mas legibles en consola.

## Comentario final

Este proyecto no busca ser un sistema productivo grande, sino una version local y entendible de un pipeline de Big Data. La gracia esta en mostrar el recorrido completo del dato: nace como fuente cruda, pasa por controles de calidad, se transforma en tablas utiles y finalmente queda documentado con metricas, catalogo y linaje.
