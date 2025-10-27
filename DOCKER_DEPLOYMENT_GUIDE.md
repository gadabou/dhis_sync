# Guide de Déploiement Docker - DHIS2 Sync Application

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Architecture Docker](#architecture-docker)
4. [Installation rapide](#installation-rapide)
5. [Configuration détaillée](#configuration-détaillée)
6. [Déploiement](#déploiement)
7. [Gestion des conteneurs](#gestion-des-conteneurs)
8. [Difficultés rencontrées et solutions](#difficultés-rencontrées-et-solutions)
9. [Maintenance](#maintenance)
10. [Dépannage](#dépannage)
11. [Sécurité](#sécurité)
12. [Production](#production)

---

## Vue d'ensemble

Ce guide décrit le déploiement de l'application DHIS2 Sync en utilisant Docker et Docker Compose. Cette approche offre:

- **Portabilité**: Fonctionne sur n'importe quelle machine avec Docker
- **Isolation**: Chaque service dans son propre conteneur
- **Reproductibilité**: Environnement identique en développement et production
- **Facilité de déploiement**: Une seule commande pour tout démarrer
- **Scalabilité**: Facile d'ajouter des workers Celery

### Stack technologique

- **Django 5.2.4** - Framework web Python
- **Gunicorn** - Serveur d'application WSGI
- **Nginx** - Serveur web et reverse proxy
- **PostgreSQL 15** - Base de données relationnelle
- **Redis 7** - Cache et broker Celery
- **Celery** - Traitement de tâches asynchrones

### Date de création
20 octobre 2025

### Version Python
Python 3.12

---

## Prérequis

### Système d'exploitation

Ce déploiement fonctionne sur:
- Linux (Ubuntu, Debian, CentOS, etc.)
- macOS
- Windows (avec WSL2)

### Logiciels requis

#### Docker

**Installation sur Ubuntu/Debian:**
```bash
# Mettre à jour les paquets
sudo apt update

# Installer les dépendances
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Ajouter la clé GPG Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Ajouter le dépôt Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installer Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Redémarrer la session ou exécuter
newgrp docker

# Vérifier l'installation
docker --version
```

**Installation sur d'autres systèmes:**
- macOS: [Docker Desktop](https://docs.docker.com/desktop/install/mac-install/)
- Windows: [Docker Desktop with WSL2](https://docs.docker.com/desktop/install/windows-install/)

#### Docker Compose

Docker Compose est inclus dans Docker Desktop. Pour Linux:

```bash
# Télécharger Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Rendre exécutable
sudo chmod +x /usr/local/bin/docker-compose

# Vérifier l'installation
docker-compose --version
```

Ou utiliser la nouvelle commande intégrée:
```bash
docker compose version
```

### Espace disque recommandé

- **Minimum**: 5 GB
- **Recommandé**: 10 GB
- **Production**: 20 GB ou plus

---

## Architecture Docker

### Diagramme de l'architecture

```
┌─────────────────────────────────────────────────┐
│                  Internet/LAN                    │
└──────────────────┬──────────────────────────────┘
                   │
              ┌────▼─────┐
              │  Nginx   │  Port 80/443
              │ Container│  (Reverse Proxy)
              └────┬─────┘
                   │
         ┌─────────▼──────────┐
         │   Django/Gunicorn  │  Port 8000
         │    Web Container   │  (Application)
         └─────┬──────────────┘
               │
    ┏━━━━━━━━━━▼━━━━━━━━━━┓
    ┃                      ┃
┌───▼────┐  ┌────▼────┐  ┌▼──────┐
│PostgreSQL Redis    │  │Celery │
│Container│ Container│  │Workers│
└─────────┘ └─────────┘  └───────┘
```

### Services Docker

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| **nginx** | nginx:1.25-alpine | 80, 443 | Reverse proxy et fichiers statiques |
| **web** | dhis2sync:latest | 8000 | Application Django avec Gunicorn |
| **db** | postgres:15-alpine | 5432 | Base de données PostgreSQL |
| **redis** | redis:7-alpine | 6379 | Cache et broker Celery |
| **celery_worker** | dhis2sync:latest | - | Worker Celery pour tâches async |
| **celery_beat** | dhis2sync:latest | - | Scheduler Celery pour tâches périodiques |

### Volumes Docker

| Volume | Montage | Description |
|--------|---------|-------------|
| **postgres_data** | /var/lib/postgresql/data | Données PostgreSQL persistantes |
| **redis_data** | /data | Données Redis persistantes |
| **static_volume** | /app/staticfiles | Fichiers statiques collectés |
| **media_volume** | /app/media | Fichiers uploadés par les utilisateurs |
| **logs_volume** | /app/logs | Logs de l'application |

### Réseau Docker

Tous les services communiquent via un réseau bridge nommé `dhis2sync_network`.

---

## Installation rapide

### 1. Cloner ou se placer dans le projet

```bash
cd "/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync"
```

### 2. Configurer les variables d'environnement

```bash
# Copier le fichier d'exemple
cp .env.docker .env

# Éditer le fichier .env
nano .env
```

**Modifier au minimum:**
- `POSTGRES_PASSWORD` - Mot de passe PostgreSQL sécurisé
- `DJANGO_SUPERUSER_PASSWORD` - Mot de passe admin Django
- `ALLOWED_HOSTS` - Votre nom de domaine

### 3. Déployer avec un seul script

```bash
./docker-deploy.sh
```

Ce script va:
1. Vérifier que Docker est installé
2. Construire les images Docker
3. Démarrer tous les conteneurs
4. Initialiser la base de données
5. Créer le superutilisateur
6. Afficher les URLs d'accès

### 4. Accéder à l'application

Ouvrez votre navigateur:
- **Application**: http://localhost:4999/
- **Admin**: http://localhost:4999/admin/
- **Dashboard**: http://localhost:4999/auto-sync/dashboard/

**Credentials par défaut:**
- Username: `admin` (ou votre DJANGO_SUPERUSER_USERNAME)
- Password: voir `.env` - DJANGO_SUPERUSER_PASSWORD

**Note:** Le port **4999** a été choisi pour éviter les conflits avec d'autres services sur le port 80.

---

## Configuration détaillée

### Fichier .env

Le fichier `.env` contient toutes les variables d'environnement nécessaires:

```bash
# ===== DJANGO SETTINGS =====
SECRET_KEY=votre-secret-key-generee-automatiquement
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# ===== DATABASE SETTINGS (PostgreSQL) =====
POSTGRES_DB=dhis2sync
POSTGRES_USER=dhis2user
POSTGRES_PASSWORD=VotreMotDePasseSecurise123!
POSTGRES_HOST=db
POSTGRES_PORT=5432

# ===== REDIS SETTINGS =====
REDIS_HOST=redis
REDIS_PORT=6379

# ===== CELERY SETTINGS =====
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# ===== SUPERUSER (créé au premier démarrage) =====
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=ChangeThisPassword123!

# ===== DHIS2 SETTINGS =====
VERIFY_SSL=true
DEFAULT_START_DATE=2025-01-01
DEFAULT_END_DATE=2025-12-31
AUTOSYNC_PROBE_EVERY_MIN=2

# ===== EMAIL SETTINGS =====
EMAIL_HOST=smtp.example.org
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=true
```

### Génération de SECRET_KEY

Pour générer une nouvelle SECRET_KEY:

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Configuration Nginx

Le fichier `docker/nginx.conf` contient la configuration Nginx. Vous pouvez le modifier pour:
- Changer les timeouts
- Activer HTTPS
- Ajouter des règles de cache
- Configurer la compression

### Configuration PostgreSQL

Par défaut, PostgreSQL utilise les paramètres du fichier `.env`. Pour une configuration avancée, vous pouvez:

1. Créer un fichier `docker/postgresql.conf`
2. Le monter dans le conteneur via `docker-compose.yml`

---

## Déploiement

### Méthode 1: Script automatisé (recommandé)

```bash
./docker-deploy.sh
```

### Méthode 2: Commandes manuelles

#### Étape 1: Préparer l'environnement

```bash
# Copier le fichier .env
cp .env.docker .env

# Éditer les variables
nano .env
```

#### Étape 2: Construire les images

```bash
# Construction sans cache (première fois)
docker-compose build --no-cache

# Ou avec cache (plus rapide pour les mises à jour)
docker-compose build
```

#### Étape 3: Démarrer les conteneurs

```bash
# Démarrer en arrière-plan
docker-compose up -d

# Ou démarrer avec logs visibles (Ctrl+C pour arrêter)
docker-compose up
```

#### Étape 4: Vérifier l'état

```bash
# Voir l'état des conteneurs
docker-compose ps

# Voir les logs
docker-compose logs -f
```

#### Étape 5: Accéder à l'application

L'application est maintenant accessible sur http://localhost:4999/

### Vérification du déploiement

```bash
# Vérifier que tous les conteneurs sont en cours d'exécution
docker-compose ps

# Vérifier les logs pour des erreurs
docker-compose logs --tail=50

# Tester l'application
curl -I http://localhost:4999/

# Tester les fichiers statiques
curl -I http://localhost:4999/static/admin/css/base.css

# Tester le health check
curl http://localhost:4999/health/

# Vérifier la santé des services
docker-compose ps | grep "healthy"
```

---

## Gestion des conteneurs

### Script de gestion

Le script `docker-manage.sh` simplifie la gestion quotidienne:

```bash
# Afficher l'aide
./docker-manage.sh help

# Démarrer
./docker-manage.sh start

# Arrêter
./docker-manage.sh stop

# Redémarrer
./docker-manage.sh restart

# Voir l'état
./docker-manage.sh status

# Voir les logs
./docker-manage.sh logs

# Voir les logs d'un service spécifique
./docker-manage.sh logs-web
./docker-manage.sh logs-nginx
./docker-manage.sh logs-celery

# Shell Django
./docker-manage.sh shell

# Shell PostgreSQL
./docker-manage.sh dbshell

# Migrations
./docker-manage.sh migrate
./docker-manage.sh makemigrations

# Collecter les fichiers statiques
./docker-manage.sh collectstatic

# Créer un superutilisateur
./docker-manage.sh createsuperuser

# Sauvegarder la base de données
./docker-manage.sh backup-db

# Restaurer la base de données
./docker-manage.sh restore-db backup_20251020_120000.sql

# Nettoyer (ATTENTION: supprime tout)
./docker-manage.sh clean

# Reconstruire
./docker-manage.sh rebuild
```

### Commandes Docker Compose utiles

```bash
# Démarrer les services
docker-compose up -d

# Arrêter les services
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v

# Redémarrer un service spécifique
docker-compose restart web

# Voir les logs d'un service
docker-compose logs -f web

# Exécuter une commande dans un conteneur
docker-compose exec web python manage.py migrate

# Voir l'utilisation des ressources
docker stats

# Construire une image spécifique
docker-compose build web

# Reconstruire tout sans cache
docker-compose build --no-cache
```

---

## Difficultés rencontrées et solutions

### 1. Chemins avec espaces dans le nom

**Problème:**
Le projet est situé dans `/home/gado/Integrate Health Dropbox/...` avec des espaces.

**Solution:**
- Utilisation systématique de guillemets dans tous les scripts
- Échappement approprié dans les configurations
- Tests approfondis avec des chemins contenant des espaces

**Impact:** Aucun problème rencontré après application de ces pratiques.

### 2. Conflits de ports avec services locaux

**Problème:**
PostgreSQL (port 5432) et Redis (port 6379) étaient déjà installés et en cours d'exécution sur l'hôte, causant des erreurs lors du démarrage des conteneurs Docker:
```
ERROR: for db  Cannot start service db: failed to bind host port for 0.0.0.0:5432
ERROR: for redis  Cannot start service redis: failed to bind host port for 0.0.0.0:6379
```

**Solution adoptée:**
Les ports PostgreSQL et Redis ont été commentés dans `docker-compose.yml`. Les services restent accessibles depuis les conteneurs Docker via le réseau interne mais ne sont pas exposés sur l'hôte.

**Code dans docker-compose.yml:**
```yaml
db:
  # ports:
  #   - "5432:5432"  # Commenté pour éviter conflit avec PostgreSQL local

redis:
  # ports:
  #   - "6379:6379"  # Commenté pour éviter conflit avec Redis local
```

**Avantages:**
- Pas de conflit de ports
- Plus sécurisé (services internes non exposés)
- Architecture standard pour la production

**Alternative:** Si vous devez accéder à ces services depuis l'hôte, utilisez des ports différents:
```yaml
db:
  ports:
    - "5433:5432"  # Port 5433 sur l'hôte → 5432 dans le conteneur

redis:
  ports:
    - "6380:6379"  # Port 6380 sur l'hôte → 6379 dans le conteneur
```

### 3. Port HTTP personnalisé (4999)

**Problème:**
Le port 80 standard peut entrer en conflit avec d'autres serveurs web ou nécessiter des privilèges administrateur.

**Solution:**
Configuration du port 4999 pour Nginx dans `docker-compose.yml`:

**Code dans docker-compose.yml:**
```yaml
nginx:
  ports:
    - "4999:80"  # HTTP sur le port 4999
```

**Impact:** L'application est accessible sur http://localhost:4999/ au lieu de http://localhost/

**Pour production:** Vous pouvez revenir au port 80 ou configurer le port 443 pour HTTPS.

### 4. Permissions des fichiers dans Docker

**Problème:**
Les fichiers créés dans le conteneur appartiennent à l'utilisateur root par défaut.

**Solution:**
- Création d'un utilisateur non-root `dhis2user` (UID 1000) dans le Dockerfile
- Utilisation de `--chown` lors de la copie des fichiers
- Configuration du service pour s'exécuter avec cet utilisateur

**Code dans le Dockerfile:**
```dockerfile
RUN useradd -m -u 1000 dhis2user
USER dhis2user
```

### 5. Attente des services dépendants

**Problème:**
Django démarre avant que PostgreSQL soit prêt, causant des erreurs de connexion.

**Solution:**
- Utilisation de health checks dans `docker-compose.yml`
- Script `entrypoint.sh` qui attend que les services soient disponibles avec `nc` (netcat)
- Utilisation de `depends_on` avec conditions `service_healthy`

**Code dans docker-compose.yml:**
```yaml
depends_on:
  db:
    condition: service_healthy
  redis:
    condition: service_healthy
```

### 6. Collecte des fichiers statiques

**Problème:**
Nginx ne peut pas accéder aux fichiers statiques de Django.

**Solution:**
- Utilisation d'un volume partagé `static_volume`
- Le conteneur `web` collecte les fichiers dans ce volume
- Le conteneur `nginx` monte ce volume en lecture seule
- Configuration des alias Nginx pour servir ces fichiers

**Configuration:**
```yaml
volumes:
  - static_volume:/app/staticfiles
```

### 7. Variables d'environnement PostgreSQL vs Django

**Problème:**
Deux façons de configurer la base de données: `DATABASE_URL` ou variables séparées.

**Solution:**
- Modification de `settings_production.py` pour supporter les deux méthodes
- Priorité aux variables d'environnement Docker individuelles (POSTGRES_HOST, etc.)
- Fallback sur DATABASE_URL si elle existe
- Fallback final sur SQLite

**Avantage:** Flexibilité maximale pour différents environnements.

### 8. Création automatique du superutilisateur

**Problème:**
Le superutilisateur doit être créé manuellement après le déploiement.

**Solution:**
- Ajout de la création automatique dans `entrypoint.sh`
- Utilisation des variables d'environnement DJANGO_SUPERUSER_*
- Vérification si le superutilisateur existe déjà

**Impact:** Déploiement complètement automatisé.

### 9. Logs et volumes persistants

**Problème:**
Les logs disparaissent quand le conteneur est recréé.

**Solution:**
- Utilisation de volumes nommés pour les logs
- Montage du répertoire `/app/logs` dans un volume persistant
- Configuration de logrotate si nécessaire

### 10. Performance de construction Docker

**Problème:**
La construction de l'image est lente, surtout l'installation des dépendances Python.

**Solution:**
- Copie de `requirements.txt` avant le reste du code (cache Docker)
- Installation des dépendances système en une seule couche RUN
- Utilisation d'images Alpine quand possible (PostgreSQL, Redis, Nginx)
- Nettoyage du cache apt dans la même couche

**Optimisation dans le Dockerfile:**
```dockerfile
# Copier requirements.txt d'abord (cache Docker)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copier le code ensuite (change souvent)
COPY . .
```

### 11. Configuration Nginx pour les requêtes longues

**Problème:**
Les synchronisations DHIS2 peuvent prendre plusieurs minutes, causant des timeouts.

**Solution:**
- Augmentation des timeouts Nginx (300 secondes)
- Augmentation du timeout Gunicorn (120 secondes)
- Configuration des buffers appropriés

**Configuration Nginx:**
```nginx
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
proxy_read_timeout 300s;
```

### 12. Compatibilité multi-plateforme

**Problème:**
Docker fonctionne différemment sur Linux, macOS et Windows.

**Solution:**
- Utilisation d'images officielles multi-architecture
- Tests sur différentes plateformes
- Documentation des particularités de chaque système
- Utilisation de chemins relatifs dans docker-compose.yml

---

## Maintenance

### Mise à jour de l'application

```bash
# 1. Arrêter les conteneurs
docker-compose down

# 2. Mettre à jour le code (git pull, etc.)
git pull origin main

# 3. Reconstruire les images
docker-compose build

# 4. Démarrer les conteneurs
docker-compose up -d

# 5. Appliquer les migrations si nécessaire
docker-compose exec web python manage.py migrate

# 6. Collecter les nouveaux fichiers statiques
docker-compose exec web python manage.py collectstatic --noinput
```

Ou simplement:
```bash
./docker-manage.sh rebuild
```

### Sauvegardes

#### Base de données PostgreSQL

```bash
# Sauvegarde automatique avec le script
./docker-manage.sh backup-db

# Ou manuellement
docker-compose exec -T db pg_dump -U dhis2user dhis2sync > backup_$(date +%Y%m%d_%H%M%S).sql

# Sauvegarde compressée
docker-compose exec -T db pg_dump -U dhis2user dhis2sync | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restauration
./docker-manage.sh restore-db backup_20251020_120000.sql

# Ou manuellement
docker-compose exec -T db psql -U dhis2user dhis2sync < backup_20251020_120000.sql
```

#### Fichiers media

```bash
# Sauvegarder les fichiers media
docker run --rm -v dhis2sync_media:/data -v $(pwd):/backup alpine tar czf /backup/media_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Restaurer les fichiers media
docker run --rm -v dhis2sync_media:/data -v $(pwd):/backup alpine tar xzf /backup/media_backup_20251020_120000.tar.gz -C /data
```

#### Sauvegarde complète

```bash
# Créer un répertoire de sauvegarde
mkdir -p backups

# Sauvegarder la base de données
docker-compose exec -T db pg_dump -U dhis2user dhis2sync | gzip > backups/db_$(date +%Y%m%d_%H%M%S).sql.gz

# Sauvegarder les volumes
docker run --rm -v dhis2sync_media:/data -v $(pwd)/backups:/backup alpine tar czf /backup/media_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
docker run --rm -v dhis2sync_logs:/data -v $(pwd)/backups:/backup alpine tar czf /backup/logs_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Sauvegarder la configuration
tar czf backups/config_$(date +%Y%m%d_%H%M%S).tar.gz .env docker-compose.yml
```

### Monitoring

#### Logs

```bash
# Tous les logs en temps réel
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f web
docker-compose logs -f nginx
docker-compose logs -f db

# Dernières 100 lignes
docker-compose logs --tail=100

# Logs avec horodatage
docker-compose logs -f --timestamps
```

#### Métriques

```bash
# Utilisation des ressources en temps réel
docker stats

# Utilisation des ressources d'un conteneur
docker stats dhis2sync_web

# Espace disque des volumes
docker system df -v

# Informations sur un conteneur
docker inspect dhis2sync_web

# Processus dans un conteneur
docker top dhis2sync_web
```

#### Health checks

```bash
# Vérifier la santé de tous les services
docker-compose ps

# Tester le endpoint health
curl http://localhost/health/

# Vérifier PostgreSQL
docker-compose exec db pg_isready -U dhis2user

# Vérifier Redis
docker-compose exec redis redis-cli ping
```

### Nettoyage

```bash
# Supprimer les conteneurs arrêtés
docker-compose down

# Supprimer les conteneurs et volumes
docker-compose down -v

# Nettoyer les images non utilisées
docker image prune -a

# Nettoyer tout (ATTENTION!)
docker system prune -a --volumes

# Utiliser le script de gestion
./docker-manage.sh clean
```

---

## Dépannage

### Problème: Conteneur ne démarre pas

**Diagnostic:**
```bash
# Voir l'état
docker-compose ps

# Voir les logs
docker-compose logs <service>

# Inspecter le conteneur
docker inspect <container_id>
```

**Causes communes:**
1. **Port déjà utilisé**
   ```bash
   # Vérifier les ports
   sudo lsof -i :80
   sudo lsof -i :8000
   sudo lsof -i :5432

   # Modifier les ports dans docker-compose.yml si nécessaire
   ```

2. **Erreur dans les variables d'environnement**
   ```bash
   # Vérifier le fichier .env
   cat .env

   # Tester avec des valeurs par défaut
   docker-compose config
   ```

3. **Problème de permissions**
   ```bash
   # Vérifier les permissions des volumes
   ls -la

   # Corriger si nécessaire
   chmod -R 755 logs/ media/
   ```

### Problème: Erreur CSRF 403 Forbidden

**Symptôme:**
```
Forbidden (403)
CSRF verification failed. Request aborted.
```

**Cause:**
Django 4.0+ nécessite la configuration explicite de `CSRF_TRUSTED_ORIGINS`, surtout avec un port non-standard comme 4999.

**Solution:**
La configuration a déjà été ajoutée dans `settings_production.py`. Si le problème persiste:

```bash
# Vérifier que la configuration est présente
docker-compose exec web python -c "from dhis_sync import settings_production; print(settings_production.CSRF_TRUSTED_ORIGINS)"

# Redémarrer le conteneur web
docker-compose restart web

# Vider le cache du navigateur (Ctrl+Shift+Delete)
# Ou utiliser le mode navigation privée
```

**Configuration actuelle:**
Le fichier `settings_production.py` contient:
```python
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:4999',
    'http://127.0.0.1:4999',
    'http://localhost',
    'http://127.0.0.1',
]
```

**Pour un domaine personnalisé:**
Ajoutez dans `.env`:
```bash
CUSTOM_DOMAIN=your-domain.com
```

Puis redémarrez:
```bash
docker-compose restart web
```

**Documentation complète:** Consultez [CSRF_FIX.md](CSRF_FIX.md) pour plus de détails.

### Problème: Base de données non accessible

**Diagnostic:**
```bash
# Vérifier que PostgreSQL est en cours d'exécution
docker-compose ps db

# Voir les logs PostgreSQL
docker-compose logs db

# Tester la connexion
docker-compose exec db psql -U dhis2user -d dhis2sync -c "SELECT 1;"
```

**Solutions:**
```bash
# Redémarrer PostgreSQL
docker-compose restart db

# Vérifier les variables d'environnement
docker-compose exec web env | grep POSTGRES

# Recréer la base de données
docker-compose down -v
docker-compose up -d
```

### Problème: Fichiers statiques ne se chargent pas

**Diagnostic:**
```bash
# Vérifier que les fichiers existent
docker-compose exec web ls -la /app/staticfiles/

# Vérifier les logs Nginx
docker-compose logs nginx

# Tester directement
curl -I http://localhost/static/admin/css/base.css
```

**Solutions:**
```bash
# Recollecte des fichiers statiques
docker-compose exec web python manage.py collectstatic --noinput --clear

# Vérifier la configuration Nginx
docker-compose exec nginx cat /etc/nginx/conf.d/default.conf

# Redémarrer Nginx
docker-compose restart nginx
```

### Problème: Celery ne traite pas les tâches

**Diagnostic:**
```bash
# Vérifier que Celery est en cours d'exécution
docker-compose ps celery_worker celery_beat

# Voir les logs Celery
docker-compose logs celery_worker
docker-compose logs celery_beat

# Vérifier Redis
docker-compose exec redis redis-cli ping
```

**Solutions:**
```bash
# Redémarrer Celery
docker-compose restart celery_worker celery_beat

# Vérifier la configuration Celery
docker-compose exec web python -c "from dhis_sync import celery; print(celery.app.conf)"

# Tester une tâche manuellement
docker-compose exec web python manage.py shell
>>> from your_app.tasks import your_task
>>> your_task.delay()
```

### Problème: Erreur "Cannot connect to Docker daemon"

**Cause:** Docker daemon n'est pas en cours d'exécution ou l'utilisateur n'a pas les permissions.

**Solutions:**
```bash
# Démarrer Docker
sudo systemctl start docker

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER
newgrp docker

# Vérifier le statut
sudo systemctl status docker
```

### Problème: "Out of memory" ou conteneur redémarre constamment

**Diagnostic:**
```bash
# Vérifier l'utilisation de la mémoire
docker stats

# Voir les logs du conteneur
docker-compose logs <service>

# Vérifier la limite de mémoire
docker inspect <container> | grep -i memory
```

**Solutions:**
```bash
# Augmenter la mémoire dans docker-compose.yml
services:
  web:
    mem_limit: 2g
    mem_reservation: 1g

# Ou limiter les workers Gunicorn
command: gunicorn ... --workers 2
```

---

## Sécurité

### Sécurité de base (configurée)

✅ **Utilisateur non-root** - Les conteneurs s'exécutent avec l'utilisateur `dhis2user`
✅ **Secrets séparés** - Utilisation du fichier `.env` (non versionné)
✅ **Health checks** - Monitoring de la santé des services
✅ **Réseau isolé** - Réseau Docker bridge privé
✅ **Volumes persistants** - Données séparées des conteneurs
✅ **DEBUG=False** - Mode production activé

### Recommandations de sécurité supplémentaires

#### 1. Variables d'environnement sensibles

**Ne jamais versionner:**
- `.env` - Ajouter à `.gitignore`
- Fichiers de sauvegarde avec mots de passe
- Clés SSL/TLS

**Utiliser Docker secrets en production:**
```yaml
secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt

services:
  db:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
```

#### 2. HTTPS avec Let's Encrypt

**Installer Certbot:**
```bash
# Sur l'hôte
sudo apt install certbot python3-certbot-nginx

# Obtenir un certificat
sudo certbot --nginx -d your-domain.com

# Ou utiliser un conteneur Certbot
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/www/html:/var/www/html \
  certbot/certbot certonly --webroot \
  -w /var/www/html -d your-domain.com
```

**Configurer Nginx pour HTTPS:**
Décommenter la section HTTPS dans `docker/nginx.conf` et monter les certificats:

```yaml
services:
  nginx:
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro
```

#### 3. Firewall

```bash
# Utiliser UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### 4. Mises à jour de sécurité

```bash
# Mettre à jour les images de base régulièrement
docker-compose pull
docker-compose up -d

# Vérifier les vulnérabilités
docker scan dhis2sync:latest

# Mettre à jour les dépendances Python
pip list --outdated
```

#### 5. Limitation des ressources

Dans `docker-compose.yml`:
```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

#### 6. Rotation des logs

```bash
# Configurer la rotation dans docker-compose.yml
services:
  web:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

#### 7. Scan de sécurité

```bash
# Installer Trivy
sudo apt install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt update
sudo apt install trivy

# Scanner l'image
trivy image dhis2sync:latest

# Scanner les vulnérabilités critiques
trivy image --severity CRITICAL,HIGH dhis2sync:latest
```

---

## Production

### Checklist de production

Avant de déployer en production, vérifiez:

- [ ] `.env` configuré avec des mots de passe forts
- [ ] `DEBUG=False` dans `.env`
- [ ] `ALLOWED_HOSTS` contient votre domaine
- [ ] HTTPS configuré avec certificat valide
- [ ] Firewall configuré (ports 80, 443 ouverts uniquement)
- [ ] Sauvegardes automatiques configurées
- [ ] Monitoring mis en place
- [ ] Logs rotatifs configurés
- [ ] Limite de ressources définie
- [ ] Health checks fonctionnent
- [ ] Documentation à jour

### Configuration recommandée pour la production

**docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  web:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 2G
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  celery_worker:
    deploy:
      replicas: 3
    restart: always

  nginx:
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro
    restart: always
```

**Démarrer en production:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Scaling

**Augmenter le nombre de workers:**
```bash
# Scale manuellement
docker-compose up -d --scale celery_worker=5

# Ou dans docker-compose.yml
services:
  celery_worker:
    deploy:
      replicas: 5
```

### Monitoring avancé

**Avec Prometheus et Grafana:**
```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Commandes utiles (récapitulatif)

```bash
# ===== DÉPLOIEMENT =====
./docker-deploy.sh                    # Déploiement automatique complet
docker-compose up -d                  # Démarrer en arrière-plan
docker-compose down                   # Arrêter
docker-compose restart                # Redémarrer

# ===== GESTION =====
./docker-manage.sh help               # Afficher l'aide
./docker-manage.sh status             # État des conteneurs
./docker-manage.sh logs               # Voir les logs
./docker-manage.sh shell              # Shell Django
./docker-manage.sh backup-db          # Sauvegarder la DB

# ===== LOGS =====
docker-compose logs -f                # Tous les logs
docker-compose logs -f web            # Logs application
docker-compose logs -f nginx          # Logs Nginx
docker-compose logs --tail=100        # Dernières 100 lignes

# ===== DJANGO =====
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py collectstatic

# ===== BASE DE DONNÉES =====
docker-compose exec db psql -U dhis2user -d dhis2sync
docker-compose exec -T db pg_dump -U dhis2user dhis2sync > backup.sql

# ===== MONITORING =====
docker stats                          # Ressources en temps réel
docker-compose ps                     # État des conteneurs
docker system df                      # Utilisation disque

# ===== NETTOYAGE =====
docker-compose down -v                # Arrêter et supprimer volumes
docker system prune -a                # Nettoyer tout
./docker-manage.sh clean              # Nettoyage complet
```

---

## Conclusion

Ce déploiement Docker offre une solution complète, portable et facile à maintenir pour l'application DHIS2 Sync.

### Avantages de cette approche

✅ **Portabilité** - Fonctionne partout où Docker est installé
✅ **Isolation** - Chaque service dans son environnement
✅ **Reproductibilité** - Environnement identique partout
✅ **Scalabilité** - Facile d'ajouter des workers
✅ **Maintenance** - Mise à jour simple avec un rebuild
✅ **Sécurité** - Isolation réseau et utilisateurs non-root
✅ **Monitoring** - Health checks intégrés

### Prochaines étapes

1. Configurer HTTPS en production
2. Mettre en place des sauvegardes automatiques
3. Configurer un monitoring avancé (Prometheus/Grafana)
4. Optimiser les performances selon la charge
5. Mettre en place une CI/CD

### Support

Pour toute question:
- Consultez ce guide
- Vérifiez les logs: `./docker-manage.sh logs`
- Consultez la section Dépannage

---

**Date de création:** 20 octobre 2025
**Version:** 1.0
**Auteur:** Claude Code

**Technologies:**
- Docker & Docker Compose
- Django 5.2.4
- PostgreSQL 15
- Redis 7
- Nginx 1.25
- Celery
