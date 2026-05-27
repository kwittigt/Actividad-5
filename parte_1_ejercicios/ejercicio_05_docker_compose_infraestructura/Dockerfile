# =============================================================
#  Dockerfile — Servicio Jupyter / Python
#  Base: jupyter/scipy-notebook (incluye NumPy, SciPy, Matplotlib)
#  Se agregan: psycopg2, SQLAlchemy, Faker, Seaborn, tabulate
# =============================================================

FROM jupyter/scipy-notebook:python-3.11

# Instalar paquetes del sistema (como root)
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Volver al usuario sin privilegios del notebook
USER $NB_UID

# Copiar e instalar dependencias Python
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Directorio de trabajo por defecto
WORKDIR /home/jovyan/work
