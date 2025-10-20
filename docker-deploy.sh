#!/bin/bash

# Script de déploiement Docker pour DHIS2 Sync
set -e

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   DHIS2 Sync - Déploiement Docker     ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker n'est pas installé!${NC}"
    echo "Installation: https://docs.docker.com/get-docker/"
    exit 1
fi

# Vérifier que Docker Compose est installé
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Docker Compose n'est pas installé!${NC}"
    echo "Installation: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker et Docker Compose sont installés${NC}"
echo ""

# Vérifier si le fichier .env existe
if [ ! -f .env ]; then
    echo -e "${YELLOW}Fichier .env non trouvé${NC}"
    echo -e "${BLUE}Copie du fichier .env.docker vers .env...${NC}"
    cp .env.docker .env
    echo -e "${GREEN}✓ Fichier .env créé${NC}"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Éditez le fichier .env et changez:${NC}"
    echo "  - POSTGRES_PASSWORD"
    echo "  - DJANGO_SUPERUSER_PASSWORD"
    echo "  - SECRET_KEY (si nécessaire)"
    echo "  - ALLOWED_HOSTS (ajoutez votre domaine)"
    echo ""
    read -p "Appuyez sur Entrée après avoir modifié .env..."
fi

echo -e "${BLUE}1. Construction des images Docker...${NC}"
docker-compose build --no-cache
echo -e "${GREEN}✓ Images construites${NC}"
echo ""

echo -e "${BLUE}2. Démarrage des conteneurs...${NC}"
docker-compose up -d
echo -e "${GREEN}✓ Conteneurs démarrés${NC}"
echo ""

echo -e "${BLUE}3. Attente du démarrage des services (30 secondes)...${NC}"
sleep 30

echo -e "${BLUE}4. Vérification de l'état des conteneurs...${NC}"
docker-compose ps
echo ""

echo -e "${BLUE}5. Vérification des logs...${NC}"
docker-compose logs --tail=20
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Déploiement terminé avec succès!    ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}L'application est accessible sur:${NC}"
echo -e "  - Application: ${YELLOW}http://localhost${NC}"
echo -e "  - Admin: ${YELLOW}http://localhost/admin/${NC}"
echo -e "  - Dashboard: ${YELLOW}http://localhost/auto-sync/dashboard/${NC}"
echo ""
echo -e "${BLUE}Commandes utiles:${NC}"
echo -e "  - Voir les logs: ${YELLOW}docker-compose logs -f${NC}"
echo -e "  - Arrêter: ${YELLOW}docker-compose down${NC}"
echo -e "  - Redémarrer: ${YELLOW}docker-compose restart${NC}"
echo -e "  - Shell Django: ${YELLOW}docker-compose exec web python manage.py shell${NC}"
echo -e "  - Migrations: ${YELLOW}docker-compose exec web python manage.py migrate${NC}"
echo ""
echo -e "${YELLOW}Credentials par défaut (si créés):${NC}"
echo -e "  - Username: admin"
echo -e "  - Password: (voir .env - DJANGO_SUPERUSER_PASSWORD)"
echo ""
