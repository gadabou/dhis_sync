# Dockerfile pour DHIS2 Sync Application
# Stage: Production

# Utiliser Python 3.12 comme image de base
FROM python:3.12-slim

# Informations sur le maintainer
LABEL maintainer="DHIS2 Sync Team"
LABEL description="DHIS2 Sync Application - Django + Gunicorn"

# Variables d'environnement Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dépendances pour PostgreSQL
    libpq-dev \
    gcc \
    # Dépendances pour Pillow
    libjpeg-dev \
    zlib1g-dev \
    # Outils réseau
    curl \
    netcat-traditional \
    # Nettoyage
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install django-redis psycopg2-binary

# Créer un utilisateur non-root pour exécuter l'application
RUN useradd -m -u 1000 dhis2user && \
    mkdir -p /app/logs /app/media /app/staticfiles && \
    chown -R dhis2user:dhis2user /app

# Copier le code de l'application
COPY --chown=dhis2user:dhis2user . .

# Copier le script d'entrée
COPY --chown=dhis2user:dhis2user docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Passer à l'utilisateur non-root
USER dhis2user

# Exposer le port Gunicorn
EXPOSE 8000

# Définir le point d'entrée
ENTRYPOINT ["/entrypoint.sh"]

# Commande par défaut: démarrer Gunicorn
CMD ["gunicorn", "dhis_sync.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--worker-class", "sync", \
     "--timeout", "120", \
     "--access-logfile", "logs/gunicorn_access.log", \
     "--error-logfile", "logs/gunicorn_error.log", \
     "--log-level", "info", \
     "--capture-output"]
