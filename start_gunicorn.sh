#!/bin/bash

# Script de démarrage Gunicorn pour DHIS2 Sync (Production)

set -e

# Couleurs pour les logs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}   DHIS2 Sync - Démarrage Production${NC}"
echo -e "${BLUE}====================================${NC}"
echo ""

# Chemin du projet
PROJECT_DIR="/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync"
cd "$PROJECT_DIR"

# Activer l'environnement virtuel
echo -e "${BLUE}Activation de l'environnement virtuel...${NC}"
source venv/bin/activate

# Variables d'environnement
export DJANGO_SETTINGS_MODULE=dhis_sync.settings_production
export PYTHONUNBUFFERED=1

# Vérifier que Redis est disponible
echo -e "${BLUE}Vérification de Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis est disponible${NC}"
else
    echo -e "${YELLOW}⚠ Redis n'est pas disponible${NC}"
    echo -e "${YELLOW}  Certaines fonctionnalités (cache, Celery) ne fonctionneront pas${NC}"
fi
echo ""

# Créer les répertoires nécessaires
echo -e "${BLUE}Création des répertoires nécessaires...${NC}"
mkdir -p logs media staticfiles
echo -e "${GREEN}✓ Répertoires créés${NC}"
echo ""

# Lancer Gunicorn
echo -e "${BLUE}Démarrage de Gunicorn...${NC}"
echo ""

# Configuration Gunicorn
# - bind: adresse et port d'écoute (localhost:8000)
# - workers: nombre de processus workers (2-4 x CPU cores)
# - worker-class: type de worker (sync pour Django)
# - timeout: timeout pour les requêtes (120 secondes)
# - access-logfile: fichier de log des accès
# - error-logfile: fichier de log des erreurs
# - capture-output: capturer stdout/stderr
# - daemon: lancer en arrière-plan (commenté pour voir les logs)

exec gunicorn dhis_sync.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile logs/gunicorn_access.log \
    --error-logfile logs/gunicorn_error.log \
    --log-level info \
    --capture-output \
    --enable-stdio-inheritance

# Note: Pour lancer en mode daemon (arrière-plan), ajouter l'option:
# --daemon
