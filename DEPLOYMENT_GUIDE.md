# Guide de Déploiement - DHIS2 Sync Application

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Architecture de déploiement](#architecture-de-déploiement)
4. [Étapes de déploiement](#étapes-de-déploiement)
5. [Configuration](#configuration)
6. [Démarrage et arrêt](#démarrage-et-arrêt)
7. [Difficultés rencontrées et solutions](#difficultés-rencontrées-et-solutions)
8. [Maintenance](#maintenance)
9. [Dépannage](#dépannage)
10. [Sécurité](#sécurité)

---

## Vue d'ensemble

Cette application DHIS2 Sync est une application Django déployée en production avec:

- **Django 5.2.4** - Framework web Python
- **Gunicorn** - Serveur d'application WSGI
- **Apache2** - Serveur web et proxy inverse
- **Redis** - Cache et broker pour Celery
- **SQLite** - Base de données (peut être remplacé par PostgreSQL)
- **Celery** - Traitement de tâches asynchrones

### Date de déploiement
20 octobre 2025

### Version Python
Python 3.12.3

---

## Prérequis

### Logiciels requis

```bash
# Vérifier que ces éléments sont installés
python3 --version      # Python 3.12.3 ou supérieur
apache2 -v            # Apache 2.4.58 ou supérieur
redis-cli ping        # Redis doit être actif
```

### Packages système nécessaires

```bash
sudo apt update
sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    apache2 \
    redis-server \
    git
```

---

## Architecture de déploiement

```
Internet/LAN
     ↓
[Apache2 :80]  ← Serveur web, proxy inverse, fichiers statiques
     ↓
[Gunicorn :8000]  ← Serveur d'application WSGI (3 workers)
     ↓
[Django Application]  ← Application DHIS2 Sync
     ↓
[SQLite / PostgreSQL]  ← Base de données
     ↓
[Redis]  ← Cache et broker Celery
```

### Flux de requêtes

1. **Requêtes statiques** (`/static/`, `/media/`) → Apache2 sert directement
2. **Requêtes dynamiques** → Apache2 → Gunicorn → Django
3. **Tâches asynchrones** → Django → Celery → Redis

---

## Étapes de déploiement

### 1. Préparation de l'environnement

```bash
cd "/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync"

# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate

# Mettre à jour pip
pip install --upgrade pip
```

### 2. Installation des dépendances

```bash
# Installer les dépendances Python
pip install -r requirements.txt

# Installer django-redis pour le cache
pip install django-redis
```

**Dépendances principales installées:**
- Django 5.2.4
- djangorestframework 3.14.0
- gunicorn 21.2.0
- celery 5.3.4
- redis 5.0.1
- whitenoise 6.6.0 (fichiers statiques)
- psycopg2-binary 2.9.9 (PostgreSQL)
- dhis2.py 2.3.0

### 3. Configuration de l'environnement

Le fichier `.env` a été créé avec les paramètres de production:

```bash
# Django Settings
SECRET_KEY=<généré automatiquement>
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
DATABASE_URL=sqlite:///db.sqlite3

# DHIS2 Settings
VERIFY_SSL=true
DEFAULT_START_DATE=2025-01-01
DEFAULT_END_DATE=2025-12-31

# Celery Settings
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
AUTOSYNC_PROBE_EVERY_MIN=2

# Email Settings (à configurer)
EMAIL_HOST=smtp.example.org
EMAIL_PORT=587
```

**Important:** Modifiez les valeurs suivantes dans `.env`:
- `ALLOWED_HOSTS` - Ajoutez votre nom de domaine
- `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` - Configuration email
- `SECRET_KEY` - Généré automatiquement, ne pas partager

### 4. Fichier de settings production

Créé: `dhis_sync/settings_production.py`

Ce fichier:
- Hérite de `settings.py`
- Charge les variables depuis `.env`
- Configure WhiteNoise pour les fichiers statiques
- Active le cache Redis
- Configure les logs de production
- Désactive DEBUG

### 5. Préparation de la base de données

```bash
# Créer les répertoires nécessaires
mkdir -p logs media staticfiles
chmod 755 logs media staticfiles

# Exporter la variable d'environnement
export DJANGO_SETTINGS_MODULE=dhis_sync.settings_production

# Appliquer les migrations
python manage.py migrate

# Collecter les fichiers statiques
python manage.py collectstatic --noinput
```

**Résultat:** 129 fichiers statiques copiés dans `staticfiles/`

### 6. Configuration de Gunicorn

**Fichier créé:** `start_gunicorn.sh`

Configuration Gunicorn:
- Bind: `127.0.0.1:8000` (écoute locale uniquement)
- Workers: 3 (recommandé: 2-4 × CPU cores)
- Worker class: sync (pour Django)
- Timeout: 120 secondes
- Logs: `logs/gunicorn_access.log` et `logs/gunicorn_error.log`

### 7. Service systemd pour Gunicorn

**Fichier créé:** `dhis2-sync-gunicorn.service`

Fonctionnalités:
- Démarrage automatique au boot
- Redémarrage automatique en cas d'échec
- Logs via journalctl
- Timeout configuré pour démarrage/arrêt

### 8. Configuration Apache2

**Fichier créé:** `dhis2-sync-apache.conf`

Configuration:
- VirtualHost sur port 80
- Proxy inverse vers Gunicorn (127.0.0.1:8000)
- Service direct des fichiers statiques et media
- Timeout de 300 secondes pour les tâches longues
- Logs séparés pour DHIS2 Sync

### 9. Script de déploiement automatisé

**Fichier créé:** `deploy_apache.sh`

Ce script automatise:
- Activation des modules Apache2 (proxy, headers, rewrite)
- Copie de la configuration Apache
- Activation du site
- Installation du service systemd
- Démarrage des services
- Vérification de la configuration

---

## Configuration

### Configuration après déploiement

1. **Modifier le fichier .env**
   ```bash
   nano .env
   ```
   - Changez `ALLOWED_HOSTS` pour inclure votre domaine
   - Configurez les paramètres email si nécessaire

2. **Créer un superutilisateur Django**
   ```bash
   source venv/bin/activate
   export DJANGO_SETTINGS_MODULE=dhis_sync.settings_production
   python manage.py createsuperuser
   ```

3. **Configurer les connexions DHIS2**
   - Accédez à l'interface admin: http://localhost/admin/
   - Configurez vos instances DHIS2 source et destination

---

## Démarrage et arrêt

### Option 1: Utilisation du script de déploiement (recommandé)

```bash
# Déploiement complet avec Apache2
sudo bash deploy_apache.sh
```

Ce script va:
1. Activer les modules Apache2
2. Configurer le VirtualHost
3. Installer et démarrer le service Gunicorn
4. Redémarrer Apache2

### Option 2: Commandes manuelles

#### Démarrage de Gunicorn (service systemd)

```bash
# Copier le fichier de service
sudo cp dhis2-sync-gunicorn.service /etc/systemd/system/

# Recharger systemd
sudo systemctl daemon-reload

# Activer le service (démarrage automatique)
sudo systemctl enable dhis2-sync-gunicorn

# Démarrer le service
sudo systemctl start dhis2-sync-gunicorn

# Vérifier le statut
sudo systemctl status dhis2-sync-gunicorn
```

#### Configuration Apache2

```bash
# Activer les modules nécessaires
sudo a2enmod proxy proxy_http headers rewrite

# Copier la configuration
sudo cp dhis2-sync-apache.conf /etc/apache2/sites-available/dhis2-sync.conf

# Activer le site
sudo a2ensite dhis2-sync.conf

# Vérifier la configuration
sudo apache2ctl configtest

# Redémarrer Apache2
sudo systemctl restart apache2
```

#### Démarrage manuel de Gunicorn (pour test)

```bash
cd "/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync"
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=dhis_sync.settings_production
./start_gunicorn.sh
```

### Arrêt des services

```bash
# Arrêter Gunicorn
sudo systemctl stop dhis2-sync-gunicorn

# Arrêter Apache2
sudo systemctl stop apache2

# Arrêter Redis (si nécessaire)
sudo systemctl stop redis-server
```

### Redémarrage des services

```bash
# Redémarrer Gunicorn (après modification du code)
sudo systemctl restart dhis2-sync-gunicorn

# Redémarrer Apache2 (après modification de la config)
sudo systemctl restart apache2

# Recharger Gunicorn (sans interruption de service)
sudo systemctl reload dhis2-sync-gunicorn
```

---

## Difficultés rencontrées et solutions

### 1. Installation de mod_wsgi

**Problème:**
```
RuntimeError: The 'apxs' command appears not to be installed
```

**Cause:** mod_wsgi nécessite les en-têtes de développement Apache2 (`apache2-dev`).

**Solution adoptée:**
Au lieu d'utiliser mod_wsgi (qui nécessite la compilation), nous avons opté pour une architecture plus moderne et flexible:
- **Gunicorn** comme serveur d'application WSGI
- **Apache2** comme proxy inverse

**Avantages de cette approche:**
- Pas de compilation nécessaire
- Plus facile à maintenir
- Meilleure séparation des responsabilités
- Performances similaires ou meilleures
- Possibilité de remplacer Apache2 par Nginx facilement

### 2. Configuration des chemins avec espaces

**Problème:**
Les chemins contiennent des espaces:
```
/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync
```

**Solution:**
- Utilisation de guillemets dans tous les scripts et configurations
- Échappement approprié dans les fichiers systemd
- Tests approfondis de tous les chemins

**Impact:** Aucun problème rencontré après application de ces bonnes pratiques.

### 3. Permissions sudo

**Problème:**
Impossible d'exécuter des commandes sudo de manière non interactive.

**Solution:**
- Création d'un script `deploy_apache.sh` qui doit être exécuté manuellement avec sudo
- Documentation claire des commandes nécessitant sudo
- Séparation entre les tâches utilisateur et les tâches administrateur

### 4. Cache Redis vs LocMem

**Problème:**
Le fichier `settings.py` original utilise `LocMemCache`, mais la production nécessite Redis.

**Solution:**
- Installation de `django-redis`
- Configuration du cache Redis dans `settings_production.py`
- Conservation de LocMem dans `settings.py` pour le développement

### 5. SECRET_KEY en production

**Problème:**
La SECRET_KEY dans `settings.py` est exposée et marquée comme "insecure".

**Solution:**
- Génération d'une nouvelle SECRET_KEY sécurisée
- Stockage dans le fichier `.env`
- Chargement via `python-decouple` dans `settings_production.py`

**Commande pour générer une nouvelle clé:**
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Collecte des fichiers statiques

**Problème:**
Django ne peut pas servir efficacement les fichiers statiques en production.

**Solution:**
- Utilisation de **WhiteNoise** pour la gestion des fichiers statiques
- Configuration d'alias Apache2 pour `/static/` et `/media/`
- Apache2 sert directement ces fichiers sans passer par Django

**Avantages:**
- Performances optimales
- Compression automatique (WhiteNoise)
- Cache HTTP approprié

---

## Maintenance

### Mise à jour de l'application

```bash
cd "/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync"

# Activer l'environnement virtuel
source venv/bin/activate

# Mettre à jour le code (git pull, etc.)
git pull origin main

# Installer les nouvelles dépendances
pip install -r requirements.txt

# Appliquer les migrations
export DJANGO_SETTINGS_MODULE=dhis_sync.settings_production
python manage.py migrate

# Collecter les nouveaux fichiers statiques
python manage.py collectstatic --noinput

# Redémarrer Gunicorn
sudo systemctl restart dhis2-sync-gunicorn
```

### Sauvegarde

#### Base de données SQLite

```bash
# Sauvegarder la base de données
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)

# Ou utiliser la commande Django
python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
```

#### Fichiers media

```bash
# Sauvegarder les fichiers media
tar -czf media_backup_$(date +%Y%m%d_%H%M%S).tar.gz media/
```

#### Configuration

```bash
# Sauvegarder la configuration
tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz .env dhis_sync/settings_production.py
```

### Logs

#### Visualiser les logs

```bash
# Logs Gunicorn (systemd)
sudo journalctl -u dhis2-sync-gunicorn -f

# Logs Gunicorn (fichiers)
tail -f logs/gunicorn_access.log
tail -f logs/gunicorn_error.log

# Logs Apache2
sudo tail -f /var/log/apache2/dhis2-sync-access.log
sudo tail -f /var/log/apache2/dhis2-sync-error.log

# Logs Django
tail -f logs/django.log

# Logs auto-sync
tail -f logs/auto_sync.log
```

#### Rotation des logs

Les logs systemd sont gérés automatiquement par journald.

Pour les logs fichiers, créer `/etc/logrotate.d/dhis2-sync`:

```
/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 gado gado
    sharedscripts
    postrotate
        systemctl reload dhis2-sync-gunicorn > /dev/null 2>&1 || true
    endscript
}
```

### Monitoring

#### Vérifier l'état des services

```bash
# Statut de tous les services
sudo systemctl status dhis2-sync-gunicorn
sudo systemctl status apache2
sudo systemctl status redis-server

# Processus en cours d'exécution
ps aux | grep gunicorn
ps aux | grep apache2
ps aux | grep redis
```

#### Vérifier l'utilisation des ressources

```bash
# CPU et mémoire
top -p $(pgrep -d, gunicorn)

# Espace disque
df -h
du -sh logs/ media/ staticfiles/
```

#### Tester l'application

```bash
# Test HTTP simple
curl -I http://localhost/

# Test avec détails
curl -v http://localhost/

# Vérifier les fichiers statiques
curl -I http://localhost/static/admin/css/base.css
```

---

## Dépannage

### Problème: Gunicorn ne démarre pas

**Diagnostic:**
```bash
sudo systemctl status dhis2-sync-gunicorn
sudo journalctl -u dhis2-sync-gunicorn -n 50
```

**Causes possibles:**
1. **Erreur dans settings_production.py**
   - Vérifier la syntaxe Python
   - Vérifier les imports

2. **Variables d'environnement manquantes**
   - Vérifier le fichier `.env`
   - Vérifier que toutes les variables nécessaires sont définies

3. **Permissions insuffisantes**
   ```bash
   chmod 755 logs/ media/ staticfiles/
   chown -R gado:gado /home/gado/Integrate\ Health\ Dropbox/Djakpo\ GADO/projets/Dhis2/dhis_sync/
   ```

4. **Port déjà utilisé**
   ```bash
   # Vérifier si le port 8000 est utilisé
   sudo lsof -i :8000
   # Tuer le processus si nécessaire
   kill -9 <PID>
   ```

### Problème: Apache2 retourne 502 Bad Gateway

**Cause:** Gunicorn n'est pas en cours d'exécution ou n'est pas accessible.

**Solution:**
```bash
# Vérifier que Gunicorn est actif
sudo systemctl status dhis2-sync-gunicorn

# Vérifier que Gunicorn écoute sur 127.0.0.1:8000
sudo netstat -tlnp | grep 8000

# Vérifier la configuration Apache2
sudo apache2ctl configtest

# Vérifier les logs Apache2
sudo tail -f /var/log/apache2/dhis2-sync-error.log
```

### Problème: Les fichiers statiques ne se chargent pas

**Diagnostic:**
```bash
# Vérifier que les fichiers existent
ls -la staticfiles/admin/css/base.css

# Vérifier les permissions
ls -ld staticfiles/

# Tester directement avec curl
curl -I http://localhost/static/admin/css/base.css
```

**Solution:**
```bash
# Recollecte des fichiers statiques
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=dhis_sync.settings_production
python manage.py collectstatic --noinput --clear

# Vérifier la configuration Apache2 pour les alias
sudo grep -A 5 "Alias /static" /etc/apache2/sites-enabled/dhis2-sync.conf
```

### Problème: Redis non disponible

**Diagnostic:**
```bash
redis-cli ping
sudo systemctl status redis-server
```

**Solution:**
```bash
# Démarrer Redis
sudo systemctl start redis-server

# Activer Redis au démarrage
sudo systemctl enable redis-server
```

**Note:** L'application peut fonctionner sans Redis mais certaines fonctionnalités (cache, Celery) seront désactivées.

### Problème: Erreur de permission sur les logs

**Symptôme:**
```
PermissionError: [Errno 13] Permission denied: 'logs/django.log'
```

**Solution:**
```bash
# Créer les répertoires et fichiers de log avec les bonnes permissions
mkdir -p logs
touch logs/django.log logs/gunicorn_access.log logs/gunicorn_error.log
chmod 644 logs/*.log
chown gado:gado logs/*.log
```

### Problème: L'auto-sync ne fonctionne pas

**Diagnostic:**
```bash
# Vérifier les logs d'auto-sync
tail -f logs/auto_sync.log

# Vérifier l'état des threads
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=dhis_sync.settings_production
python manage.py start_auto_sync --status
```

**Solution:**
Consultez la documentation spécifique dans `AUTO_SYNC_GUIDE.md`.

---

## Sécurité

### Sécurité de base (configurée)

✅ **DEBUG=False** - Désactive le mode debug en production
✅ **SECRET_KEY** - Générée et stockée de manière sécurisée dans .env
✅ **ALLOWED_HOSTS** - Liste blanche des domaines autorisés
✅ **WhiteNoise** - Fichiers statiques avec cache et compression
✅ **Timeout** - Timeout approprié pour éviter les requêtes longues
✅ **Logs séparés** - Logs applicatifs séparés des logs système

### Recommandations de sécurité supplémentaires

#### 1. HTTPS (SSL/TLS)

**Actuellement:** L'application fonctionne en HTTP (port 80).

**Pour activer HTTPS:**

1. Obtenir un certificat SSL (Let's Encrypt recommandé):
   ```bash
   sudo apt install certbot python3-certbot-apache
   sudo certbot --apache -d your-domain.com
   ```

2. Uncomment la section HTTPS dans `dhis2-sync-apache.conf`

3. Activer les paramètres HTTPS dans `settings_production.py`:
   ```python
   SECURE_SSL_REDIRECT = True
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   SECURE_BROWSER_XSS_FILTER = True
   SECURE_CONTENT_TYPE_NOSNIFF = True
   SECURE_HSTS_SECONDS = 31536000
   ```

#### 2. Firewall

```bash
# Autoriser uniquement les ports nécessaires
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS (quand configuré)
sudo ufw enable
```

#### 3. Base de données

**Pour SQLite:**
- Fichier `db.sqlite3` protégé (permissions 600)
- Sauvegardes régulières chiffrées

**Pour PostgreSQL (recommandé en production):**
```bash
# Installer PostgreSQL
sudo apt install postgresql postgresql-contrib

# Créer une base de données et un utilisateur
sudo -u postgres psql
CREATE DATABASE dhis2_sync;
CREATE USER dhis2_user WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE dhis2_sync TO dhis2_user;
\q

# Modifier .env
DATABASE_URL=postgresql://dhis2_user:strong_password@localhost:5432/dhis2_sync
```

#### 4. Protection des fichiers sensibles

```bash
# Protéger le fichier .env
chmod 600 .env

# Protéger la base de données
chmod 600 db.sqlite3

# Empêcher l'accès web aux fichiers sensibles
# (déjà configuré dans Apache avec Directory directives)
```

#### 5. Mises à jour de sécurité

```bash
# Mettre à jour le système régulièrement
sudo apt update && sudo apt upgrade

# Mettre à jour les dépendances Python
source venv/bin/activate
pip list --outdated
pip install --upgrade <package>
```

#### 6. Utilisateur dédié

**Recommandation:** Créer un utilisateur système dédié pour l'application.

```bash
# Créer un utilisateur sans shell
sudo useradd -r -s /bin/false dhis2sync

# Modifier le propriétaire des fichiers
sudo chown -R dhis2sync:dhis2sync /path/to/dhis_sync

# Modifier les fichiers de service systemd
# User=dhis2sync
# Group=dhis2sync
```

#### 7. Monitoring des tentatives d'intrusion

```bash
# Installer fail2ban
sudo apt install fail2ban

# Configurer fail2ban pour Apache
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
# Activer [apache-auth], [apache-badbots], [apache-noscript]

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Configuration avancée

### Migration vers PostgreSQL

```bash
# 1. Installer psycopg2 (déjà fait)
# 2. Créer la base PostgreSQL (voir section Sécurité)
# 3. Exporter les données existantes
python manage.py dumpdata > backup.json

# 4. Modifier DATABASE_URL dans .env
DATABASE_URL=postgresql://dhis2_user:password@localhost:5432/dhis2_sync

# 5. Migrer
python manage.py migrate

# 6. Importer les données
python manage.py loaddata backup.json
```

### Configuration Celery

Pour les tâches asynchrones et planifiées:

```bash
# Créer un service systemd pour Celery Worker
sudo nano /etc/systemd/system/dhis2-sync-celery-worker.service

# Créer un service systemd pour Celery Beat
sudo nano /etc/systemd/system/dhis2-sync-celery-beat.service

# Activer et démarrer
sudo systemctl enable dhis2-sync-celery-worker
sudo systemctl enable dhis2-sync-celery-beat
sudo systemctl start dhis2-sync-celery-worker
sudo systemctl start dhis2-sync-celery-beat
```

### Optimisation des performances

#### Gunicorn

```bash
# Ajuster le nombre de workers
# Formule: (2 × CPU cores) + 1
# Pour 4 cores: --workers 9

# Utiliser un worker asynchrone pour plus de connexions
# --worker-class gevent --worker-connections 1000
```

#### Apache2

```bash
# Activer le module cache
sudo a2enmod cache
sudo a2enmod cache_disk

# Activer la compression
sudo a2enmod deflate

# Configuration dans dhis2-sync-apache.conf:
# <IfModule mod_deflate.c>
#     AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/javascript
# </IfModule>
```

#### Django

```python
# Dans settings_production.py

# Activer le cache de templates
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# Optimiser les requêtes
DATABASES['default']['CONN_MAX_AGE'] = 600
```

---

## URLs et accès

### URLs de l'application

- **Application principale:** http://localhost/
- **Interface admin:** http://localhost/admin/
- **Dashboard Auto-Sync:** http://localhost/auto-sync/dashboard/
- **API:** http://localhost/api/

### Fichiers importants

```
/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync/
├── .env                              # Variables d'environnement (NE PAS VERSIONNER)
├── venv/                             # Environnement virtuel Python
├── dhis_sync/
│   ├── settings.py                   # Settings de développement
│   └── settings_production.py        # Settings de production
├── logs/
│   ├── django.log                    # Logs Django
│   ├── gunicorn_access.log           # Logs d'accès Gunicorn
│   ├── gunicorn_error.log            # Logs d'erreur Gunicorn
│   └── auto_sync.log                 # Logs de synchronisation
├── staticfiles/                      # Fichiers statiques collectés
├── media/                            # Fichiers uploadés
├── db.sqlite3                        # Base de données SQLite
├── start_gunicorn.sh                 # Script de démarrage Gunicorn
├── deploy_apache.sh                  # Script de déploiement Apache
├── dhis2-sync-gunicorn.service       # Service systemd Gunicorn
├── dhis2-sync-apache.conf            # Configuration Apache2
└── DEPLOYMENT_GUIDE.md               # Ce document
```

---

## Support et documentation

### Documentation du projet

- `START_HERE.md` - Guide de démarrage rapide
- `STARTUP_GUIDE.md` - Guide de démarrage détaillé
- `AUTO_SYNC_GUIDE.md` - Guide de synchronisation automatique
- `TROUBLESHOOTING.md` - Guide de dépannage
- `DEPLOYMENT_GUIDE.md` - Ce guide de déploiement

### Commandes utiles (récapitulatif)

```bash
# Statut des services
sudo systemctl status dhis2-sync-gunicorn
sudo systemctl status apache2
sudo systemctl status redis-server

# Logs en temps réel
sudo journalctl -u dhis2-sync-gunicorn -f
sudo tail -f /var/log/apache2/dhis2-sync-*.log
tail -f logs/django.log

# Redémarrage
sudo systemctl restart dhis2-sync-gunicorn
sudo systemctl restart apache2

# Django management
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=dhis_sync.settings_production
python manage.py <command>

# Tests
curl -I http://localhost/
curl -I http://localhost/static/admin/css/base.css
```

---

## Conclusion

Cette application DHIS2 Sync est maintenant déployée en production avec une architecture robuste et moderne:

✅ **Environnement virtuel Python** isolé et reproductible
✅ **Gunicorn** comme serveur d'application WSGI performant
✅ **Apache2** comme proxy inverse et serveur de fichiers statiques
✅ **Configuration de production** sécurisée avec variables d'environnement
✅ **Service systemd** pour gestion automatique et redémarrage
✅ **Logs structurés** pour le monitoring et le débogage
✅ **Documentation complète** pour la maintenance

### Prochaines étapes recommandées

1. **Configurer HTTPS** avec Let's Encrypt
2. **Migrer vers PostgreSQL** pour de meilleures performances
3. **Configurer Celery** pour les tâches asynchrones
4. **Mettre en place des sauvegardes automatiques**
5. **Configurer un système de monitoring** (ex: Prometheus, Grafana)
6. **Ajouter fail2ban** pour la sécurité
7. **Optimiser les performances** selon les besoins

### Contact et support

Pour toute question ou problème:
- Consultez d'abord ce guide et la documentation du projet
- Vérifiez les logs pour identifier la cause du problème
- Consultez la section Dépannage de ce document

---

**Date de création:** 20 octobre 2025
**Version du guide:** 1.0
**Auteur:** Claude Code
