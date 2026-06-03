# Mini infraestructura de datos con Docker Compose

Este ejercicio arma una pequena infraestructura local para trabajar con datos usando Docker Compose. La idea es levantar varios servicios que normalmente se usan en un entorno de ciencia de datos: una base PostgreSQL, un JupyterLab para ejecutar codigo Python y pgAdmin para revisar la base desde una interfaz web.

El caso de prueba es un sistema simple de ventas. Primero se inicializa una base de datos con tablas e indices, despues se cargan datos sinteticos y finalmente se ejecutan consultas para generar un reporte de analisis.

## Que contiene el proyecto

```text
.
|-- docker-compose.yml
|-- Dockerfile
|-- requirements.txt
|-- init.sql
|-- load_data.py
|-- query_analysis.py
|-- .env
`-- README.md
```

Cada archivo cumple una parte del ejercicio:

- `docker-compose.yml`: define los servicios, red interna, volumenes persistentes y variables de entorno.
- `Dockerfile`: crea la imagen de Jupyter con las dependencias necesarias para conectarse a PostgreSQL y analizar datos.
- `requirements.txt`: lista las librerias Python que se instalan dentro del contenedor de Jupyter.
- `init.sql`: crea el esquema `ventas`, las tablas, los indices y una vista de reporte diario.
- `load_data.py`: genera productos y transacciones sinteticas, las carga en PostgreSQL y exporta una muestra CSV.
- `query_analysis.py`: ejecuta consultas SQL, arma tablas de analisis con Pandas y guarda un reporte de texto.
- `.env`: guarda las credenciales y configuraciones usadas por Docker Compose.

## Servicios de la infraestructura

La infraestructura queda compuesta por tres servicios:

| Servicio | Para que sirve | Puerto |
| --- | --- | --- |
| `postgres` | Base de datos principal del ejercicio. | `5432` |
| `jupyter` | Entorno Python/JupyterLab para correr scripts y notebooks. | `8888` |
| `pgadmin` | Interfaz web para administrar PostgreSQL. | `5050` |

Los contenedores se conectan entre si por una red interna llamada `ds_network`. Dentro de esa red, Jupyter y pgAdmin se conectan a la base usando el nombre del servicio: `postgres`.

## Variables principales

Las variables estan en `.env` para no repetirlas dentro del `docker-compose.yml`.

```env
DB_USER=dsuser
DB_PASSWORD=dspassword
DB_NAME=dsdb
JUPYTER_TOKEN=datascience2024
PGADMIN_EMAIL=admin@ds.local
PGADMIN_PASSWORD=adminpass
```

Estas credenciales son solo para desarrollo local. En un entorno real no convendria dejarlas asi en texto plano.

## Base de datos

El archivo `init.sql` se ejecuta automaticamente cuando PostgreSQL crea el volumen por primera vez. Ahi se define el esquema `ventas` con dos tablas:

- `ventas.productos`: guarda el catalogo de productos, categoria y precio unitario.
- `ventas.transacciones`: guarda ventas con producto, cantidad, fecha, region, canal y total.

Tambien se crean indices para acelerar busquedas por fecha, producto y region. Al final se define la vista `ventas.reporte_diario`, que resume ventas por fecha, categoria, region y canal.

## Script de carga

`load_data.py` genera datos sinteticos de ventas. El script:

1. Espera hasta que PostgreSQL este disponible.
2. Inserta una lista base de productos.
3. Genera 2.000 transacciones aleatorias durante el anio 2024.
4. Guarda las transacciones en `ventas.transacciones`.
5. Exporta una muestra de datos en `/home/jovyan/datasets/ventas_muestra.csv`.

La carga esta pensada para no duplicar datos si ya existen productos o transacciones en la base.

## Script de analisis

`query_analysis.py` se ejecuta despues de cargar los datos. Consulta PostgreSQL y genera un reporte con:

- resumen general de ventas;
- ingresos por categoria;
- ventas por region;
- ventas por canal;
- top 5 productos por ingresos;
- tendencia mensual;
- ventas por dia de la semana;
- tabla pivot de ingresos por region y canal.

El resultado se guarda en:

```text
/home/jovyan/datasets/reporte.txt
```

Esa ruta vive dentro del volumen `datasets_data`, por lo que el reporte se mantiene aunque se apaguen los contenedores.

## Como ejecutar

Desde la carpeta del ejercicio:

```bash
docker compose up --build
```

En otra terminal se puede revisar que todo este arriba:

```bash
docker compose ps
```

Luego se carga la informacion:

```bash
docker compose exec jupyter python /home/jovyan/scripts/load_data.py
```

Y se ejecuta el analisis:

```bash
docker compose exec jupyter python /home/jovyan/scripts/query_analysis.py
```

Para ver el reporte:

```bash
docker compose exec jupyter cat /home/jovyan/datasets/reporte.txt
```

## Acceso web

| Herramienta | URL | Acceso |
| --- | --- | --- |
| JupyterLab | `http://localhost:8888` | token `datascience2024` |
| pgAdmin | `http://localhost:5050` | `admin@ds.local` / `adminpass` |

Para registrar la base en pgAdmin:

1. Abrir `http://localhost:5050`.
2. Iniciar sesion con las credenciales de `.env`.
3. Crear un servidor nuevo.
4. Usar `postgres` como host.
5. Usar puerto `5432`, base `dsdb`, usuario `dsuser` y clave `dspassword`.

Es importante usar `postgres` como host, porque dentro de Docker Compose los servicios se encuentran por nombre. `localhost` apuntaria al contenedor de pgAdmin, no al contenedor de PostgreSQL.

## Comandos utiles

Ver logs:

```bash
docker compose logs postgres
docker compose logs jupyter
docker compose logs -f
```

Entrar a PostgreSQL:

```bash
docker compose exec postgres psql -U dsuser -d dsdb
```

Consultas rapidas dentro de `psql`:

```sql
\dt ventas.*
SELECT COUNT(*) FROM ventas.transacciones;
SELECT * FROM ventas.reporte_diario LIMIT 10;
```

Apagar los contenedores sin borrar datos:

```bash
docker compose down
```

Apagar y borrar volumenes:

```bash
docker compose down -v
```

El segundo comando elimina los datos persistentes, asi que conviene usarlo solo cuando se quiera reiniciar el ejercicio desde cero.

## Volumenes y persistencia

El compose declara cuatro volumenes:

| Volumen | Uso |
| --- | --- |
| `postgres_data` | Datos internos de PostgreSQL. |
| `notebooks_data` | Archivos creados dentro de Jupyter. |
| `datasets_data` | CSVs y reportes generados por los scripts. |
| `pgadmin_data` | Configuracion de pgAdmin. |

Gracias a estos volumenes, los datos no se pierden al ejecutar `docker compose down`. Solo se eliminan si se usa `docker compose down -v`.

## Nota sobre la estructura actual

En la carpeta actual los archivos estan en la raiz. Si `docker-compose.yml` apunta a rutas como `./jupyter`, `./postgres` o `./scripts`, esas carpetas deben existir o se deben ajustar las rutas del compose. La idea original es:

```text
jupyter/Dockerfile
jupyter/requirements.txt
postgres/init.sql
scripts/load_data.py
scripts/query_analysis.py
```

Si se mantiene la estructura plana, el compose debe cambiarse para apuntar directamente a `./Dockerfile`, `./requirements.txt`, `./init.sql`, `./load_data.py` y `./query_analysis.py`.

## Que demuestra este ejercicio

Este ejercicio muestra como Docker Compose ayuda a levantar un entorno completo sin instalar PostgreSQL, Jupyter y pgAdmin manualmente en el computador. Tambien permite practicar conceptos importantes: variables de entorno, redes internas, volumenes persistentes, healthchecks, carga de datos y analisis reproducible.

No es una infraestructura de produccion. No tiene alta disponibilidad, backups automaticos, secretos seguros ni monitoreo avanzado. Es un entorno local para aprender y probar una arquitectura pequena de datos.
