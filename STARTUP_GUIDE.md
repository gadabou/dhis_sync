# Guide de démarrage - DHIS2 Sync

Ce guide explique comment démarrer l'application DHIS2 Sync avec la synchronisation automatique.

## 🚀 Démarrage rapide

### Option 1: Démarrage simple (Développement)

Le plus simple pour le développement, lance uniquement Django avec auto-sync:

```bash
# Rendre le script exécutable
chmod +x start_simple.sh

# Démarrer
./start_simple.sh
```

**Caractéristiques:**
- Serveur Django sur http://localhost:8000
- Auto-sync avec threads Python natifs
- Pas besoin de Redis ou Celery
- Idéal pour le développement

### Option 2: Démarrage complet (Production)

Lance Django + Celery Worker + Celery Beat:

```bash
# Rendre le script exécutable
chmod +x start.sh

# Démarrer
./start.sh
```

**Prérequis:**
- Redis doit être installé et démarré
- Si Redis n'est pas disponible, le script passe automatiquement en mode simple

**Caractéristiques:**
- Serveur Django sur http://localhost:8000
- Celery Worker pour les tâches asynchrones
- Celery Beat pour les tâches périodiques
- Plus robuste pour la production

### Option 3: Commande Django classique

```bash
python manage.py runserver
```

**Note:** La synchronisation automatique se lance automatiquement après 5 secondes.

## 📋 Ce qui se passe au démarrage

1. **Django démarre** (0-5 secondes)
2. **Auto-sync s'initialise** (après 5 secondes)
   - Charge toutes les configurations en mode `automatic`
   - Vérifie que `is_active=True` et `auto_sync_settings.is_enabled=True`
   - Démarre un thread de monitoring pour chaque configuration
3. **Monitoring actif**
   - Vérifie les changements selon l'intervalle configuré
   - Déclenche les synchronisations automatiquement

## 🎛️ Configuration

### Vérifier les configurations auto-sync

```bash
# Lister les configurations
python manage.py start_auto_sync --list

# Voir le statut
python manage.py start_auto_sync --status
```

### Créer une configuration auto-sync

1. Via l'interface web: http://localhost:8000
2. Créer une `SyncConfiguration` avec `execution_mode='automatic'`
3. Configurer les paramètres auto-sync
4. Activer la configuration

### Contrôler manuellement l'auto-sync

```bash
# Démarrer pour toutes les configs
python manage.py start_auto_sync

# Démarrer pour une config spécifique
python manage.py start_auto_sync 1

# Arrêter toutes les syncs
python manage.py stop_auto_sync

# Arrêter une sync spécifique
python manage.py stop_auto_sync 1
```

## 📊 Monitoring

### Dashboard Web

Accédez au dashboard auto-sync:
- URL: http://localhost:8000/auto-sync/dashboard/
- Voir l'état de toutes les configurations
- Contrôler les synchronisations
- Auto-refresh toutes les 10 secondes

### Logs

Les logs sont disponibles dans le dossier `logs/`:

```bash
# Logs de synchronisation automatique
tail -f logs/auto_sync.log

# Logs généraux de l'application
tail -f logs/dhis2_sync.log

# Logs Celery (si utilisé)
tail -f logs/celery_worker.log
tail -f logs/celery_beat.log
```

### Vérifier les threads actifs

```python
from dhis_app.services.auto_sync.scheduler import get_auto_sync_status

# Status global
status = get_auto_sync_status()
print(f"Threads actifs: {status['total_active']}")

# Status d'une config spécifique
status = get_auto_sync_status(sync_config_id=1)
print(f"Running: {status['is_running']}")
```

## 🔧 Installation de Redis (pour Celery)

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

### macOS

```bash
brew install redis
brew services start redis
```

### Vérifier Redis

```bash
redis-cli ping
# Devrait retourner: PONG
```

## 🐳 Démarrage avec Docker (optionnel)

Si vous préférez utiliser Docker:

```bash
# À venir - fichier docker-compose.yml
```

## 🔄 Service systemd (Production Linux)

Pour démarrer automatiquement au boot du serveur:

```bash
# Copier le fichier de service
sudo cp dhis_sync.service /etc/systemd/system/

# Recharger systemd
sudo systemctl daemon-reload

# Activer le service
sudo systemctl enable dhis_sync

# Démarrer le service
sudo systemctl start dhis_sync

# Vérifier le statut
sudo systemctl status dhis_sync

# Voir les logs
sudo journalctl -u dhis_sync -f
```

## ⚙️ Variables d'environnement (Production)

Pour la production, créez un fichier `.env`:

```bash
# Django
SECRET_KEY=votre-clé-secrète-production
DEBUG=False
ALLOWED_HOSTS=votre-domaine.com

# Base de données (si PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=dhis_sync
DB_USER=dhis_user
DB_PASSWORD=mot-de-passe-sécurisé
DB_HOST=localhost
DB_PORT=5432

# Redis/Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# DHIS2
DHIS2_TIMEOUT=300
```

## 🛠️ Dépannage

### L'auto-sync ne démarre pas

1. Vérifiez les logs: `tail -f logs/dhis2_sync.log`
2. Vérifiez qu'il y a des configurations en mode `automatic`
3. Vérifiez que `is_active=True` et `auto_sync_settings.is_enabled=True`

```bash
python manage.py start_auto_sync --list
```

### Celery ne se connecte pas à Redis

1. Vérifiez que Redis est démarré: `redis-cli ping`
2. Vérifiez les paramètres dans `settings.py`
3. Utilisez le mode simple sans Celery: `./start_simple.sh`

### Les threads ne s'arrêtent pas

```bash
# Nettoyer les threads morts
curl http://localhost:8000/api/auto-sync/cleanup/

# Ou via Python
python manage.py shell
>>> from dhis_app.services.auto_sync.scheduler import AutoSyncScheduler
>>> scheduler = AutoSyncScheduler.get_instance()
>>> scheduler.stop()  # Arrête tous les threads
```

### Double démarrage avec le reloader Django

C'est normal en développement. Le système utilise un cache pour éviter le double démarrage du même thread.

## 📚 Documentation supplémentaire

- [AUTO_SYNC_GUIDE.md](AUTO_SYNC_GUIDE.md) - Guide complet de la synchronisation automatique
- [CELERY_MIGRATION.md](CELERY_MIGRATION.md) - Migration vers Celery
- [LOGGING_AND_CELERY.md](LOGGING_AND_CELERY.md) - Configuration des logs et Celery

## 🆘 Support

En cas de problème:
1. Consultez les logs dans `logs/`
2. Vérifiez le statut: `python manage.py start_auto_sync --status`
3. Redémarrez l'application: `./start_simple.sh`

---

**Bon développement! 🚀**