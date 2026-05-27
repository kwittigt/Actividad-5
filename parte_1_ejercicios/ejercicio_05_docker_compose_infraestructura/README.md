# Ejercicio 5 — Mini Infraestructura con Docker Compose para Ciencia de Datos

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                     HOST (tu máquina)               │
│                                                     │
│  :8888 ──► [JupyterLab]  ──┐                        │
│  :5432 ──► [PostgreSQL]    ├── ds_network (bridge)  │
│  :5050 ──► [pgAdmin]     ──┘                        │
│                                                     │
│  Volúmenes:                                         │
│   postgres_data  → datos persistentes de PG         │
│   notebooks_data → notebooks de Jupyter             │
│   datasets_data  → CSVs y reportes generados        │
│   pgadmin_data   → config de pgAdmin                │
└─────────────────────────────────────────────────────┘
```

---

## Servicios, puertos y variables de entorno

| Servicio   | Imagen               | Puerto host | Puerto interno | Variables clave                                         |
|------------|----------------------|-------------|----------------|---------------------------------------------------------|
| `postgres` | postgres:15-alpine   | 5432        | 5432           | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`    |
| `jupyter`  | (build local)        | 8888        | 8888           | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `JUPYTER_TOKEN` |
| `pgadmin`  | dpage/pgadmin4:8     | 5050        | 80             | `PGADMIN_DEFAULT_EMAIL`, `PGADMIN_DEFAULT_PASSWORD`     |

> Las variables están centralizadas en el archivo `.env` para no repetirlas en el YAML.

---

## Estructura del proyecto

```
ejercicio5/
├── docker-compose.yml          ← orquestación principal
├── .env                        ← variables de entorno
├── postgres/
│   └── init.sql                ← esquema + tablas + vistas (auto-ejecutado al crear el volumen)
├── jupyter/
│   ├── Dockerfile              ← imagen Python personalizada
│   └── requirements.txt        ← dependencias pip
└── scripts/
    ├── load_data.py            ← genera dataset sintético y lo carga en PG
    └── query_analysis.py       ← corre consultas SQL + análisis Pandas → reporte .txt
```

---

## Comandos de ejecución

### 1. Levantar toda la infraestructura

```bash
docker compose up --build
# --build reconstruye la imagen de Jupyter si cambió el Dockerfile o requirements.txt
```

### 2. Verificar que los servicios están corriendo

```bash
docker compose ps
```

Salida esperada:
```
NAME           IMAGE                  STATUS          PORTS
ds_jupyter     ejercicio5-jupyter     Up              0.0.0.0:8888->8888/tcp
ds_pgadmin     dpage/pgadmin4:8       Up              0.0.0.0:5050->80/tcp
ds_postgres    postgres:15-alpine     Up (healthy)    0.0.0.0:5432->5432/tcp
```

### 3. Cargar el dataset

```bash
docker compose exec jupyter python /home/jovyan/scripts/load_data.py
```

### 4. Ejecutar el análisis

```bash
docker compose exec jupyter python /home/jovyan/scripts/query_analysis.py
```

### 5. Verificar persistencia del volumen

```bash
# El reporte queda en el volumen datasets_data
docker compose exec jupyter cat /home/jovyan/datasets/reporte.txt
```

### 6. Ver logs de un servicio

```bash
docker compose logs postgres    # logs de PostgreSQL
docker compose logs jupyter     # logs de Jupyter (incluye el token de acceso)
docker compose logs -f          # todos los servicios, en tiempo real
```

### 7. Conectarse a PostgreSQL directamente

```bash
docker compose exec postgres psql -U dsuser -d dsdb
```

Dentro de psql:
```sql
-- Verificar tablas
\dt ventas.*

-- Contar registros
SELECT COUNT(*) FROM ventas.transacciones;

-- Ver la vista de reporte diario
SELECT * FROM ventas.reporte_diario LIMIT 10;
```

### 8. Bajar la infraestructura

```bash
docker compose down          # detiene y elimina contenedores; los VOLÚMENES se conservan
docker compose down -v       # elimina también los volúmenes (BORRA TODOS LOS DATOS)
```

---

## Evidencia de persistencia

Los volúmenes de Docker son directorios gestionados en el host (`/var/lib/docker/volumes/`).  
Para verificar que persisten datos después de detener los contenedores:

```bash
# 1. Bajar sin -v (conserva volúmenes)
docker compose down

# 2. Subir de nuevo SIN --build
docker compose up

# 3. Los datos siguen ahí
docker compose exec jupyter python /home/jovyan/scripts/query_analysis.py
# → imprime el reporte con los mismos datos sin volver a cargar
```

---

## Acceso a las interfaces web

| Interfaz   | URL                          | Credencial                               |
|------------|------------------------------|------------------------------------------|
| JupyterLab | http://localhost:8888        | Token: `datascience2024`                 |
| pgAdmin    | http://localhost:5050        | admin@ds.local / adminpass               |

### Configurar pgAdmin (primera vez)

1. Abrir http://localhost:5050
2. Click en *Add New Server*
3. En **General**: nombre `ds_postgres`
4. En **Connection**:
   - Host: `postgres` *(nombre del servicio, no localhost)*
   - Port: `5432`
   - Database: `dsdb`
   - Username: `dsuser`
   - Password: `dspassword`

> **Nota clave**: dentro de la red `ds_network`, los contenedores se resuelven entre sí  
> por **nombre de servicio**. Desde pgAdmin o Jupyter, el host de PostgreSQL es `postgres`, no `localhost`.

---

## Dependencias entre servicios

```
postgres ──(healthcheck OK)──► jupyter
postgres ──(healthcheck OK)──► pgadmin
```

El servicio `jupyter` usa `depends_on` con `condition: service_healthy`,  
lo que garantiza que no intenta conectarse a PostgreSQL antes de que esté listo.

---

## ¿Qué resuelve Docker Compose en este ejercicio?

| Problema                          | ¿Lo resuelve? | Cómo                                              |
|-----------------------------------|:-------------:|---------------------------------------------------|
| Reproducibilidad del entorno      | ✅            | Imagen fija + requirements.txt versionado         |
| Comunicación entre servicios      | ✅            | Red bridge interna `ds_network`                   |
| Persistencia de datos             | ✅            | Volúmenes nombrados que sobreviven a `down`       |
| Configuración sin hardcoding      | ✅            | Variables de entorno en `.env`                    |
| Arranque ordenado de servicios    | ✅            | `depends_on` + healthcheck                        |
| Aislamiento del entorno local     | ✅            | Los servicios no modifican el sistema anfitrión   |

## ¿Qué NO resuelve Docker Compose?

| Problema                              | Razón                                                                 |
|---------------------------------------|-----------------------------------------------------------------------|
| **Escalabilidad distribuida**         | Compose es mono-host; para múltiples nodos se usa Kubernetes o Swarm |
| **Alta disponibilidad / failover**    | No hay réplicas ni balanceador de carga                               |
| **Seguridad de producción**           | Credenciales en `.env`, sin TLS interno, sin gestión de secretos      |
| **Monitoreo y alertas**              | No incluye Prometheus/Grafana ni sistema de métricas                  |
| **Gobierno de datos**                 | No hay control de acceso granular, auditoría ni linaje de datos        |
| **Backup automático**                 | Los volúmenes se pueden perder con `down -v`; no hay backup policy    |

> Docker Compose es una **herramienta de desarrollo local y prototipado**, no un sustituto  
> de plataformas de orquestación empresarial (Kubernetes, Airflow, MLflow, etc.).
