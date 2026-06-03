# Evaluacion arquitectonica de Big Data

Este programa es una aplicacion interactiva hecha con Streamlit para comparar distintas arquitecturas de Big Data. La idea es no elegir una tecnologia "porque si", sino evaluar varias alternativas usando criterios ponderados y ver como cambia el ranking cuando cambian las prioridades.

La app esta en `app.py` y funciona como una matriz multicriterio visual. Permite ajustar pesos, revisar puntajes, ver graficos y leer recomendaciones segun distintos escenarios.

## Que compara la aplicacion

El programa evalua cinco alternativas arquitectonicas:

| Opcion | Arquitectura | Idea general |
| --- | --- | --- |
| A | Local | Scripts, notebooks y archivos locales. |
| B | Docker | Pipeline reproducible con Docker, Parquet y herramientas columnarias. |
| C | Microservicios | Kafka, Spark/Flink, servicios separados y Kubernetes. |
| D | Lakehouse | Data Lake con Delta Lake o Iceberg, catalogo y procesamiento distribuido. |
| E | Cloud / Hibrida | Servicios administrados como BigQuery, Snowflake o Redshift. |

Cada alternativa recibe puntajes de 1 a 5 en distintos criterios. Luego esos puntajes se combinan con los pesos definidos por el usuario.

## Criterios usados

La evaluacion considera 10 criterios:

- Rendimiento
- Costo relativo
- Escalabilidad
- Mantenibilidad
- Reproducibilidad
- Gobernanza
- Seguridad
- Resiliencia
- Complejidad operacional
- Madurez requerida del equipo

Los criterios marcados con flecha hacia abajo en la app se interpretan al reves: una mayor puntuacion significa que la alternativa es mejor porque requiere menos complejidad o menos madurez previa.

## Como funciona el calculo

Los pesos iniciales estan definidos en `INIT_W`. En la interfaz aparecen como sliders, por lo que se pueden modificar sin tocar el codigo.

La app normaliza automaticamente los pesos para que sumen 100%. Despues calcula una puntuacion ponderada para cada arquitectura:

```text
puntuacion_total = suma(puntaje_del_criterio * peso_normalizado)
```

Con eso se genera el ranking final. El maximo teorico es 5.00.

## Partes principales de la interfaz

La aplicacion muestra:

1. Una descripcion breve de las cinco arquitecturas.
2. Sliders para cambiar la importancia de cada criterio.
3. Una justificacion de las ponderaciones iniciales.
4. La matriz de evaluacion completa.
5. Un ranking multicriterio en grafico de barras.
6. Un grafico radar con fortalezas y debilidades de cada arquitectura.
7. Recomendaciones segun escenarios concretos.
8. Una discusion de trade-offs y limitaciones del metodo.

## Como ejecutar

Primero hay que instalar las dependencias:

```bash
pip install streamlit pandas plotly
```

Luego, desde la carpeta del ejercicio:

```bash
streamlit run app.py
```

Streamlit abrira la app en el navegador. Normalmente queda disponible en:

```text
http://localhost:8501
```

## Dependencias

El programa usa:

- `streamlit` para construir la interfaz web.
- `pandas` para armar las tablas de datos.
- `plotly` para los graficos interactivos.

## Como interpretar los resultados

El ranking no dice que una arquitectura sea "la mejor" en todos los casos. Lo que muestra es cual alternativa conviene mas bajo los pesos actuales.

Por ejemplo, si se prioriza mucho el costo, una solucion local o Docker puede subir en el ranking. Si se prioriza escalabilidad, seguridad y gobernanza, las opciones Lakehouse o Cloud suelen quedar mejor posicionadas.

Esto es justamente lo importante del ejercicio: la arquitectura depende del contexto. No se elige igual para un equipo pequeno con pocos recursos que para una organizacion regulada o con datos a escala masiva.

## Limitaciones

La matriz simplifica la realidad. Los puntajes son ordinales y no capturan todos los factores posibles, como lock-in de proveedor, observabilidad, latencia de ingesta, costos a varios anos o experiencia real del equipo.

Aun asi, sirve como punto de partida para justificar una decision arquitectonica de manera mas ordenada y transparente.
