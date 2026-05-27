FROM python:3.11.9-slim

LABEL maintainer="INFB6074-Pipeline"
LABEL description="Pipeline Big Data local - E-commerce Analytics"
LABEL version="1.0.0"

# Evitar prompts interactivos durante la instalación
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /work

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python primero (cache layer)
COPY requirements.txt .
RUN pip install --upgrade pip==24.0 && \
    pip install -r requirements.txt

# Copiar el código fuente
COPY pipeline/ ./pipeline/
COPY data/ ./data/

# Crear directorios de zonas si no existen
RUN mkdir -p bronze silver gold metadata metrics

# Punto de entrada: ejecutar el pipeline completo
CMD ["python", "pipeline/main.py"]
