# Démarrage Rapide Docker - DHIS2 Sync

## En 3 minutes chrono!

### Prérequis

Assurez-vous que Docker et Docker Compose sont installés:
```bash
docker --version
docker-compose --version
```

Si pas installé, voir la section [Installation Docker](DOCKER_DEPLOYMENT_GUIDE.md#prérequis)

---

## Étape 1: Configuration (30 secondes)

```bash
# Copier le fichier de configuration
cp .env.docker .env

# Éditer les mots de passe (optionnel mais recommandé)
nano .env
```

**Changez au minimum:**
- `POSTGRES_PASSWORD` - Votre mot de passe sécurisé
- `DJANGO_SUPERUSER_PASSWORD` - Mot de passe admin
- `ALLOWED_HOSTS` - Votre domaine (si applicable)

---

## Étape 2: Déploiement (2 minutes)

### Option A: Script automatique (recommandé)

```bash
./docker-deploy.sh
```

### Option B: Commandes manuelles

```bash
# Construire les images
docker-compose build

# Démarrer tous les services
docker-compose up -d

# Attendre 30 secondes que tout démarre

# Vérifier l'état
docker-compose ps
```

---

## Étape 3: Accès (maintenant!)

Ouvrez votre navigateur:

- **Application**: http://localhost:4999/
- **Admin**: http://localhost:4999/admin/
- **Dashboard**: http://localhost:4999/auto-sync/dashboard/

**Note:** L'application utilise le port **4999** pour éviter les conflits avec d'autres services.

**Credentials:**
- Username: `admin` (ou votre DJANGO_SUPERUSER_USERNAME)
- Password: voir `.env` → DJANGO_SUPERUSER_PASSWORD

---

## Commandes essentielles

```bash
# Voir les logs
docker-compose logs -f

# Arrêter
docker-compose down

# Redémarrer
docker-compose restart

# Voir l'état
docker-compose ps

# Aide complète
./docker-manage.sh help
```

---

## Architecture déployée

```
┌─────────┐
│ Nginx   │ :80  ← Reverse proxy
└────┬────┘
     │
┌────▼────┐
│ Django  │ :8000 ← Application
└────┬────┘
     │
┌────▼────┬──────────┬─────────┐
│PostgreSQL│  Redis   │ Celery  │
└─────────┴──────────┴─────────┘
```

---

## Que fait le déploiement?

✅ Construit l'image Docker de l'application
✅ Lance PostgreSQL (base de données)
✅ Lance Redis (cache)
✅ Lance Django avec Gunicorn (application)
✅ Lance Celery (tâches asynchrones)
✅ Lance Nginx (serveur web)
✅ Applique les migrations de base de données
✅ Collecte les fichiers statiques
✅ Crée le superutilisateur admin

---

## Problèmes courants

### Port 4999 déjà utilisé?

**Par défaut, l'application utilise le port 4999**. Si ce port est déjà utilisé:

```bash
# Vérifier quel processus utilise le port 4999
sudo lsof -i :4999

# Changer le port dans docker-compose.yml
# Ouvrez docker-compose.yml et modifiez:
nginx:
  ports:
    - "8080:80"  # Utiliser le port 8080 à la place

# Accès: http://localhost:8080/
```

### Conflits PostgreSQL/Redis?

**Si vous avez PostgreSQL ou Redis installés localement:**

Les ports internes (5432 et 6379) sont déjà commentés dans `docker-compose.yml` pour éviter les conflits. Les services Docker utilisent un réseau interne et n'entrent pas en conflit avec vos services locaux.

**Erreur: "port already in use"?**
```bash
# Arrêter les services locaux temporairement
sudo systemctl stop postgresql
sudo systemctl stop redis-server

# Ou modifier docker-compose.yml pour utiliser des ports différents
db:
  ports:
    - "5433:5432"  # PostgreSQL sur port 5433

redis:
  ports:
    - "6380:6379"  # Redis sur port 6380
```

### Docker pas installé?

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

**Autre système:**
Voir: https://docs.docker.com/get-docker/

### Les conteneurs ne démarrent pas?

```bash
# Voir les erreurs
docker-compose logs

# Reconstruire tout
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## Gestion quotidienne

### Script de gestion

```bash
# Afficher l'aide
./docker-manage.sh help

# Commandes courantes
./docker-manage.sh status      # État
./docker-manage.sh logs        # Logs temps réel
./docker-manage.sh restart     # Redémarrer
./docker-manage.sh backup-db   # Sauvegarder DB
./docker-manage.sh shell       # Shell Django
```

### Mise à jour du code

```bash
# Mettre à jour et redéployer
git pull
./docker-manage.sh rebuild
```

### Sauvegardes

```bash
# Sauvegarder la base de données
./docker-manage.sh backup-db

# Fichier créé: backup_YYYYMMDD_HHMMSS.sql

# Restaurer
./docker-manage.sh restore-db backup_20251020_120000.sql
```

---

## Prochaines étapes

1. **Configurer DHIS2**: Accédez à l'admin et configurez vos instances DHIS2
2. **Sauvegardes automatiques**: Mettez en place un cron job
3. **HTTPS**: Configurez SSL/TLS pour la production
4. **Monitoring**: Suivez les logs et performances

---

## Documentation complète

Pour tous les détails, consultez:
- [**DOCKER_DEPLOYMENT_GUIDE.md**](DOCKER_DEPLOYMENT_GUIDE.md) - Guide complet
  - Architecture détaillée
  - Configuration avancée
  - Difficultés rencontrées et solutions
  - Sécurité
  - Production
  - Dépannage

---

## Support

**Problème?**
1. Consultez les logs: `./docker-manage.sh logs`
2. Vérifiez l'état: `./docker-manage.sh status`
3. Lisez le guide: [DOCKER_DEPLOYMENT_GUIDE.md](DOCKER_DEPLOYMENT_GUIDE.md)

---

**Bon déploiement! 🚀**
