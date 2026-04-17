FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    libproj-dev \
    libgdal-dev \
    libgeos-dev \
    libpq-dev \
    postgresql-client \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for GDAL/GEOS
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so

WORKDIR /app

# Copy requirements first for better caching
COPY climweb/requirements/base.txt ./requirements.txt

# Install Python dependencies - use psycopg2-binary to avoid compilation
RUN pip install --upgrade pip && \
    pip install django-environ gunicorn psycopg2-binary && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Install the package in editable mode
RUN pip install -e climweb/

# Collect static files
WORKDIR /app/climweb/src
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Start command - Railway will override PORT
CMD ["gunicorn", "climweb.config.wsgi:application", "--bind", "0.0.0.0:8000"]
