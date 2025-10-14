#!/bin/bash

# Script de démarrage simple pour DHIS2 Sync
# Lance uniquement le serveur Django avec auto-sync (sans Celery)

set -e

# Couleurs pour les logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}     DHIS2 Sync - Démarrage simple   ${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

echo -e "${BLUE}Mode:${NC} Développement (sans Celery)"
echo -e "${BLUE}Auto-sync:${NC} Activé avec threads Python"
echo ""

# Vérifier que le dossier logs existe
if [ ! -d "logs" ]; then
    mkdir -p logs
    echo -e "${GREEN}✓ Dossier logs/ créé${NC}"
fi

echo -e "${BLUE}Démarrage du serveur Django...${NC}"
echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}   Serveur démarré avec succès      ${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo -e "${BLUE}URL:${NC} http://localhost:8000"
echo -e "${BLUE}Dashboard:${NC} http://localhost:8000/auto-sync/dashboard/"
echo ""
echo -e "${YELLOW}La synchronisation automatique démarre dans 5 secondes...${NC}"
echo -e "${YELLOW}Consultez les logs: logs/auto_sync.log${NC}"
echo ""
echo -e "${RED}Appuyez sur Ctrl+C pour arrêter${NC}"
echo ""

# Lancer Django
python manage.py runserver 0.0.0.0:8000