# Usar una imagen base de Python oficial y ligera (basada en Debian Slim)
FROM python:3.11-slim

# Variables de entorno para optimizar Python en contenedores
# PYTHONDONTWRITEBYTECODE: Evita que se generen archivos .pyc en el contenedor
# PYTHONUNBUFFERED: Permite que los logs de la app se vean en tiempo real en Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias
# libpq-dev y gcc: Requeridos para compilar el driver de PostgreSQL (psycopg2)
# libmagic1: Requerida por la librería python-magic en Linux para identificar tipos de archivos
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Instalación de dependencias de Python
# Se copia primero requirements.txt para aprovechar la caché de capas de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copiar el código fuente del proyecto al contenedor
COPY . .

# El puerto 5000 es el estándar de Flask (y el que mapeamos en el servidor)
EXPOSE 5000

# Comando de inicio: Usamos Gunicorn como servidor de aplicaciones WSGI para producción
# --bind 0.0.0.0:5000 permite que la app sea accesible desde fuera del contenedor
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
