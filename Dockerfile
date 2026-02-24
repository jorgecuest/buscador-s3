# Usar una imagen base de Python oficial y ligera
FROM python:3.11-slim

# Evitar que Python genere archivos .pyc y permitir logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2 (PostgreSQL)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copiar el resto del código de la aplicación
COPY . .

# Exponer el puerto que usará Flask (por defecto 5000)
EXPOSE 5000

# Comando para ejecutar la aplicación usando Gunicorn (servidor de producción)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
