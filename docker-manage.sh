#!/bin/bash

# Script de gestion Docker pour DHIS2 Sync

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Fonction d'aide
show_help() {
    echo -e "${BLUE}DHIS2 Sync - Gestion Docker${NC}"
    echo ""
    echo "Usage: ./docker-manage.sh [COMMAND]"
    echo ""
    echo "Commandes disponibles:"
    echo "  start         Démarrer tous les conteneurs"
    echo "  stop          Arrêter tous les conteneurs"
    echo "  restart       Redémarrer tous les conteneurs"
    echo "  status        Afficher l'état des conteneurs"
    echo "  logs          Afficher les logs (temps réel)"
    echo "  logs-web      Afficher les logs de l'application web"
    echo "  logs-nginx    Afficher les logs Nginx"
    echo "  logs-celery   Afficher les logs Celery"
    echo "  shell         Ouvrir un shell Django"
    echo "  dbshell       Ouvrir un shell PostgreSQL"
    echo "  migrate       Appliquer les migrations"
    echo "  makemigrations Créer de nouvelles migrations"
    echo "  collectstatic Collecter les fichiers statiques"
    echo "  createsuperuser Créer un superutilisateur"
    echo "  backup-db     Sauvegarder la base de données"
    echo "  restore-db    Restaurer la base de données"
    echo "  clean         Nettoyer les conteneurs et volumes"
    echo "  rebuild       Reconstruire et redémarrer"
    echo "  help          Afficher cette aide"
    echo ""
}

# Vérifier l'argument
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

COMMAND=$1

case $COMMAND in
    start)
        echo -e "${BLUE}Démarrage des conteneurs...${NC}"
        docker-compose up -d
        echo -e "${GREEN}✓ Conteneurs démarrés${NC}"
        docker-compose ps
        ;;

    stop)
        echo -e "${YELLOW}Arrêt des conteneurs...${NC}"
        docker-compose down
        echo -e "${GREEN}✓ Conteneurs arrêtés${NC}"
        ;;

    restart)
        echo -e "${YELLOW}Redémarrage des conteneurs...${NC}"
        docker-compose restart
        echo -e "${GREEN}✓ Conteneurs redémarrés${NC}"
        docker-compose ps
        ;;

    status)
        echo -e "${BLUE}État des conteneurs:${NC}"
        docker-compose ps
        echo ""
        echo -e "${BLUE}Utilisation des ressources:${NC}"
        docker stats --no-stream
        ;;

    logs)
        echo -e "${BLUE}Logs en temps réel (Ctrl+C pour quitter):${NC}"
        docker-compose logs -f
        ;;

    logs-web)
        echo -e "${BLUE}Logs de l'application web:${NC}"
        docker-compose logs -f web
        ;;

    logs-nginx)
        echo -e "${BLUE}Logs Nginx:${NC}"
        docker-compose logs -f nginx
        ;;

    logs-celery)
        echo -e "${BLUE}Logs Celery:${NC}"
        docker-compose logs -f celery_worker celery_beat
        ;;

    shell)
        echo -e "${BLUE}Ouverture du shell Django...${NC}"
        docker-compose exec web python manage.py shell
        ;;

    dbshell)
        echo -e "${BLUE}Ouverture du shell PostgreSQL...${NC}"
        docker-compose exec db psql -U dhis2user -d dhis2sync
        ;;

    migrate)
        echo -e "${BLUE}Application des migrations...${NC}"
        docker-compose exec web python manage.py migrate
        echo -e "${GREEN}✓ Migrations appliquées${NC}"
        ;;

    makemigrations)
        echo -e "${BLUE}Création des migrations...${NC}"
        docker-compose exec web python manage.py makemigrations
        echo -e "${GREEN}✓ Migrations créées${NC}"
        ;;

    collectstatic)
        echo -e "${BLUE}Collecte des fichiers statiques...${NC}"
        docker-compose exec web python manage.py collectstatic --noinput
        echo -e "${GREEN}✓ Fichiers statiques collectés${NC}"
        ;;

    createsuperuser)
        echo -e "${BLUE}Création d'un superutilisateur...${NC}"
        docker-compose exec web python manage.py createsuperuser
        ;;

    backup-db)
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
        echo -e "${BLUE}Sauvegarde de la base de données vers $BACKUP_FILE...${NC}"
        docker-compose exec -T db pg_dump -U dhis2user dhis2sync > "$BACKUP_FILE"
        echo -e "${GREEN}✓ Base de données sauvegardée dans $BACKUP_FILE${NC}"
        ;;

    restore-db)
        if [ -z "$2" ]; then
            echo -e "${RED}Erreur: Spécifiez le fichier de sauvegarde${NC}"
            echo "Usage: ./docker-manage.sh restore-db <backup_file.sql>"
            exit 1
        fi
        BACKUP_FILE=$2
        if [ ! -f "$BACKUP_FILE" ]; then
            echo -e "${RED}Erreur: Fichier $BACKUP_FILE non trouvé${NC}"
            exit 1
        fi
        echo -e "${YELLOW}Restauration de la base de données depuis $BACKUP_FILE...${NC}"
        docker-compose exec -T db psql -U dhis2user dhis2sync < "$BACKUP_FILE"
        echo -e "${GREEN}✓ Base de données restaurée${NC}"
        ;;

    clean)
        echo -e "${RED}ATTENTION: Ceci va supprimer tous les conteneurs et volumes!${NC}"
        read -p "Êtes-vous sûr? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Nettoyage en cours...${NC}"
            docker-compose down -v
            docker system prune -f
            echo -e "${GREEN}✓ Nettoyage terminé${NC}"
        else
            echo -e "${BLUE}Opération annulée${NC}"
        fi
        ;;

    rebuild)
        echo -e "${BLUE}Reconstruction et redémarrage...${NC}"
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        echo -e "${GREEN}✓ Reconstruction terminée${NC}"
        docker-compose ps
        ;;

    help)
        show_help
        ;;

    *)
        echo -e "${RED}Commande inconnue: $COMMAND${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
