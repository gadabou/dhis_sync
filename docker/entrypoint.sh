#!/bin/bash

# Script d'entrée pour le conteneur Docker Django
set -e

echo "======================================="
echo "  DHIS2 Sync - Démarrage du conteneur  "
echo "======================================="
echo ""

# Fonction pour attendre un service
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3

    echo "En attente de $service ($host:$port)..."
    while ! nc -z "$host" "$port" > /dev/null 2>&1; do
        sleep 1
    done
    echo "✓ $service est disponible"
}

# Attendre PostgreSQL (si configuré)
if [ -n "$POSTGRES_HOST" ]; then
    wait_for_service "${POSTGRES_HOST}" "${POSTGRES_PORT:-5432}" "PostgreSQL"
fi

# Attendre Redis (si configuré)
if [ -n "$REDIS_HOST" ]; then
    wait_for_service "${REDIS_HOST}" "${REDIS_PORT:-6379}" "Redis"
fi

echo ""
echo "Initialisation de l'application..."

# Créer les répertoires nécessaires
mkdir -p logs media staticfiles
echo "✓ Répertoires créés"

# Appliquer les migrations de base de données
echo ""
echo "Application des migrations..."
python manage.py migrate --noinput
echo "✓ Migrations appliquées"

# Collecter les fichiers statiques
echo ""
echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear
echo "✓ Fichiers statiques collectés"

# Créer un superutilisateur si les variables sont définies
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo ""
    echo "Création du superutilisateur..."
    python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('✓ Superutilisateur créé')
else:
    print('✓ Superutilisateur existe déjà')
END
fi

echo ""
echo "======================================="
echo "  Initialisation terminée avec succès  "
echo "======================================="
echo ""
echo "Démarrage de l'application..."
echo ""

# Exécuter la commande passée en argument (CMD du Dockerfile)
exec "$@"
