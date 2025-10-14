#!/bin/bash

# Script de démarrage complet pour DHIS2 Sync
# Lance Celery Worker, Celery Beat et le serveur Django

set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}   DHIS2 Sync - Démarrage complet   ${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Fonction pour nettoyer les processus en cas d'arrêt
cleanup() {
    echo -e "\n${YELLOW}Arrêt des processus...${NC}"

    if [ ! -z "$CELERY_WORKER_PID" ]; then
        echo -e "${YELLOW}Arrêt du Celery Worker...${NC}"
        kill $CELERY_WORKER_PID 2>/dev/null || true
    fi

    if [ ! -z "$CELERY_BEAT_PID" ]; then
        echo -e "${YELLOW}Arrêt du Celery Beat...${NC}"
        kill $CELERY_BEAT_PID 2>/dev/null || true
    fi

    if [ ! -z "$DJANGO_PID" ]; then
        echo -e "${YELLOW}Arrêt du serveur Django...${NC}"
        kill $DJANGO_PID 2>/dev/null || true
    fi

    echo -e "${GREEN}Tous les processus ont été arrêtés${NC}"
    exit 0
}

# Capturer SIGINT (Ctrl+C) et SIGTERM
trap cleanup SIGINT SIGTERM

# Vérifier si Redis est disponible (optionnel, pour Celery)
echo -e "${BLUE}Vérification de Redis...${NC}"
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓ Redis est disponible${NC}"
        USE_CELERY=true
    else
        echo -e "${YELLOW}⚠ Redis n'est pas démarré${NC}"
        echo -e "${YELLOW}  Celery sera désactivé${NC}"
        USE_CELERY=false
    fi
else
    echo -e "${YELLOW}⚠ Redis n'est pas installé${NC}"
    echo -e "${YELLOW}  Celery sera désactivé${NC}"
    USE_CELERY=false
fi

echo ""

# Démarrer Celery Worker (si Redis est disponible)
if [ "$USE_CELERY" = true ]; then
    echo -e "${BLUE}Démarrage du Celery Worker...${NC}"
    celery -A dhis_sync worker --loglevel=info --logfile=logs/celery_worker.log &
    CELERY_WORKER_PID=$!
    echo -e "${GREEN}✓ Celery Worker démarré (PID: $CELERY_WORKER_PID)${NC}"
    echo ""

    # Attendre que le worker soit prêt
    sleep 3

    # Démarrer Celery Beat (planificateur de tâches périodiques)
    echo -e "${BLUE}Démarrage du Celery Beat...${NC}"
    celery -A dhis_sync beat --loglevel=info --logfile=logs/celery_beat.log &
    CELERY_BEAT_PID=$!
    echo -e "${GREEN}✓ Celery Beat démarré (PID: $CELERY_BEAT_PID)${NC}"
    echo ""

    # Attendre que beat soit prêt
    sleep 2
else
    echo -e "${YELLOW}Celery désactivé - La synchronisation automatique utilisera les threads Python${NC}"
    echo ""
fi

# Démarrer le serveur Django
echo -e "${BLUE}Démarrage du serveur Django...${NC}"
python manage.py runserver 0.0.0.0:8000 &
DJANGO_PID=$!
echo -e "${GREEN}✓ Serveur Django démarré (PID: $DJANGO_PID)${NC}"
echo ""

# Afficher les informations
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}   Tous les services sont démarrés  ${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo -e "${BLUE}Serveur Django:${NC} http://localhost:8000"
echo -e "${BLUE}Dashboard Auto-Sync:${NC} http://localhost:8000/auto-sync/dashboard/"
echo ""

if [ "$USE_CELERY" = true ]; then
    echo -e "${BLUE}Services Celery:${NC}"
    echo -e "  - Worker PID: $CELERY_WORKER_PID"
    echo -e "  - Beat PID: $CELERY_BEAT_PID"
    echo -e "  - Logs: logs/celery_worker.log et logs/celery_beat.log"
    echo ""
fi

echo -e "${YELLOW}Note:${NC} La synchronisation automatique démarre dans 5 secondes..."
echo -e "${YELLOW}      Consultez les logs dans logs/auto_sync.log${NC}"
echo ""
echo -e "${RED}Appuyez sur Ctrl+C pour arrêter tous les services${NC}"
echo ""

# Attendre que tous les processus se terminent
wait