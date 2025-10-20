#!/bin/bash

# Script de déploiement Apache2 pour DHIS2 Sync
# Ce script doit être exécuté avec sudo

set -e

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   Déploiement Apache2 - DHIS2 Sync   ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Vérifier si le script est exécuté avec sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Ce script doit être exécuté avec sudo${NC}"
    echo -e "${YELLOW}Usage: sudo bash deploy_apache.sh${NC}"
    exit 1
fi

PROJECT_DIR="/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync"

echo -e "${BLUE}1. Activation des modules Apache2 nécessaires...${NC}"
a2enmod proxy
a2enmod proxy_http
a2enmod headers
a2enmod rewrite
echo -e "${GREEN}✓ Modules activés${NC}"
echo ""

echo -e "${BLUE}2. Copie de la configuration Apache2...${NC}"
cp "$PROJECT_DIR/dhis2-sync-apache.conf" /etc/apache2/sites-available/dhis2-sync.conf
echo -e "${GREEN}✓ Configuration copiée vers /etc/apache2/sites-available/dhis2-sync.conf${NC}"
echo ""

echo -e "${BLUE}3. Désactivation du site par défaut (optionnel)...${NC}"
read -p "Voulez-vous désactiver le site par défaut d'Apache? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    a2dissite 000-default.conf
    echo -e "${GREEN}✓ Site par défaut désactivé${NC}"
else
    echo -e "${YELLOW}Site par défaut conservé${NC}"
fi
echo ""

echo -e "${BLUE}4. Activation du site DHIS2 Sync...${NC}"
a2ensite dhis2-sync.conf
echo -e "${GREEN}✓ Site activé${NC}"
echo ""

echo -e "${BLUE}5. Vérification de la configuration Apache2...${NC}"
apache2ctl configtest
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Configuration Apache2 valide${NC}"
else
    echo -e "${RED}✗ Erreur dans la configuration Apache2${NC}"
    echo -e "${YELLOW}Veuillez corriger les erreurs avant de continuer${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}6. Installation du service systemd pour Gunicorn...${NC}"
cp "$PROJECT_DIR/dhis2-sync-gunicorn.service" /etc/systemd/system/
systemctl daemon-reload
echo -e "${GREEN}✓ Service systemd installé${NC}"
echo ""

echo -e "${BLUE}7. Activation et démarrage du service Gunicorn...${NC}"
systemctl enable dhis2-sync-gunicorn.service
systemctl start dhis2-sync-gunicorn.service
echo -e "${GREEN}✓ Service Gunicorn activé et démarré${NC}"
echo ""

echo -e "${BLUE}8. Vérification du statut du service Gunicorn...${NC}"
systemctl status dhis2-sync-gunicorn.service --no-pager
echo ""

echo -e "${BLUE}9. Redémarrage d'Apache2...${NC}"
systemctl restart apache2
echo -e "${GREEN}✓ Apache2 redémarré${NC}"
echo ""

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Déploiement terminé avec succès!   ${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${BLUE}L'application est maintenant accessible sur:${NC}"
echo -e "  - ${YELLOW}http://localhost${NC}"
echo -e "  - ${YELLOW}http://127.0.0.1${NC}"
echo ""
echo -e "${BLUE}Commandes utiles:${NC}"
echo -e "  - Statut Gunicorn: ${YELLOW}sudo systemctl status dhis2-sync-gunicorn${NC}"
echo -e "  - Redémarrer Gunicorn: ${YELLOW}sudo systemctl restart dhis2-sync-gunicorn${NC}"
echo -e "  - Logs Gunicorn: ${YELLOW}sudo journalctl -u dhis2-sync-gunicorn -f${NC}"
echo -e "  - Logs Apache: ${YELLOW}sudo tail -f /var/log/apache2/dhis2-sync-*.log${NC}"
echo -e "  - Statut Apache: ${YELLOW}sudo systemctl status apache2${NC}"
echo ""
