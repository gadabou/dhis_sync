# Guide de Migration vers Celery pour la Production

## Pourquoi migrer vers Celery ?

Le système actuel utilise des **threads Python** pour la synchronisation automatique, ce qui est suffisant pour le développement mais présente des limitations en production:

### Limitations des threads Python

- ❌ Pas de persistance (threads perdus au redémarrage)
- ❌ Difficile à monitorer
- ❌ Pas de retry automatique avancé
- ❌ Scalabilité limitée
- ❌ Pas de priorités de tâches

### Avantages de Celery

- ✅ Persistance des tâches (survit aux redémarrages)
- ✅ Monitoring avancé (Flower, Prometheus)
- ✅ Retry automatique avec backoff exponentiel
- ✅ Scalabilité horizontale (workers multiples)
- ✅ Priorités et routage de tâches
- ✅ Tâches périodiques robustes (Celery Beat)
- ✅ Gestion des erreurs avancée

## Prérequis

### 1. Installer Redis

Redis est utilisé comme broker de messages pour Celery.

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# macOS
brew install redis

# Démarrer Redis
sudo systemctl start redis    # Linux
brew services start redis      # macOS

# Vérifier que Redis fonctionne
redis-cli ping
# Doit retourner: PONG
```

### 2. Installer les packages Python

```bash
pip install celery redis django-celery-beat django-celery-results django-redis
```

Ou ajouter à `requirements.txt`:
```
celery==5.3.4
redis==5.0.1
django-celery-beat==2.5.0
django-celery-results==2.5.1
django-redis==5.4.0
```

Puis:
```bash
pip install -r requirements.txt
```

## Étapes de migration

### Étape 1: Activer Celery dans Django

#### 1.1 Décommenter dans `dhis_sync/__init__.py`

```python
# Décommenter ces lignes:
from .celery import app as celery_app
__all__ = ('celery_app',)
```

#### 1.2 Activer la configuration dans `settings.py`

Décommenter la section Celery:

```python
# ===== CELERY CONFIGURATION =====
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max par tâche
```

#### 1.3 Activer le cache Redis (optionnel mais recommandé)

Dans `settings.py`, remplacer le cache par Redis:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### Étape 2: Ajouter Celery aux INSTALLED_APPS

Dans `settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dhis_app',
    'django_celery_beat',      # <-- Ajouter
    'django_celery_results',   # <-- Ajouter
]
```

### Étape 3: Migrer la base de données

```bash
python manage.py migrate django_celery_beat
python manage.py migrate django_celery_results
```

### Étape 4: Démarrer les workers Celery

#### 4.1 Worker principal (dans un terminal)

```bash
celery -A dhis_sync worker --loglevel=info
```

#### 4.2 Celery Beat (dans un autre terminal)

```bash
celery -A dhis_sync beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Étape 5: Adapter le code auto-sync

#### 5.1 Remplacer les imports dans `tasks.py`

Remplacer les fonctions threading par les tâches Celery.

Dans `dhis_app/services/auto_sync/tasks.py`, décommenter la section Celery et utiliser:

```python
from .celery_tasks import (
    celery_trigger_auto_sync,
    celery_monitor_and_sync,
    celery_monitor_all_configs,
    celery_cleanup_dead_tasks,
    celery_health_check,
)
```

#### 5.2 Modifier les vues pour utiliser Celery

Dans `dhis_app/views/auto_sync.py`, remplacer:

```python
# Avant (threading)
trigger_auto_sync_async(sync_config_id)

# Après (Celery)
from dhis_app.services.auto_sync.celery_tasks import celery_trigger_auto_sync
celery_trigger_auto_sync.delay(sync_config_id)
```

### Étape 6: Configuration du démarrage automatique

#### 6.1 Créer des services systemd

**Worker Celery** (`/etc/systemd/system/celery-worker.service`):

```ini
[Unit]
Description=Celery Worker for DHIS2 Sync
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/dhis_sync
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A dhis_sync worker \
    --loglevel=info \
    --logfile=/var/log/celery/worker.log \
    --pidfile=/var/run/celery/worker.pid \
    --detach
ExecStop=/path/to/venv/bin/celery -A dhis_sync worker --pidfile=/var/run/celery/worker.pid --stop
Restart=always

[Install]
WantedBy=multi-user.target
```

**Celery Beat** (`/etc/systemd/system/celery-beat.service`):

```ini
[Unit]
Description=Celery Beat for DHIS2 Sync
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/dhis_sync
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A dhis_sync beat \
    --loglevel=info \
    --logfile=/var/log/celery/beat.log \
    --pidfile=/var/run/celery/beat.pid \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 6.2 Activer et démarrer les services

```bash
# Créer les répertoires
sudo mkdir -p /var/log/celery /var/run/celery
sudo chown www-data:www-data /var/log/celery /var/run/celery

# Activer les services
sudo systemctl enable celery-worker
sudo systemctl enable celery-beat

# Démarrer les services
sudo systemctl start celery-worker
sudo systemctl start celery-beat

# Vérifier le statut
sudo systemctl status celery-worker
sudo systemctl status celery-beat
```

## Monitoring avec Flower

Flower est une interface web pour monitorer Celery.

### Installation

```bash
pip install flower
```

### Démarrage

```bash
celery -A dhis_sync flower --port=5555
```

Accéder à: `http://localhost:5555`

### Service systemd pour Flower

**Flower** (`/etc/systemd/system/celery-flower.service`):

```ini
[Unit]
Description=Flower for Celery
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/dhis_sync
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A dhis_sync flower --port=5555
Restart=always

[Install]
WantedBy=multi-user.target
```

## Vérification post-migration

### 1. Vérifier que les workers sont actifs

```bash
celery -A dhis_sync inspect active
```

### 2. Vérifier les tâches périodiques

```bash
celery -A dhis_sync inspect scheduled
```

### 3. Tester une tâche

```python
from dhis_app.services.auto_sync.celery_tasks import celery_health_check

# Lancer la tâche
result = celery_health_check.delay()

# Vérifier le résultat
print(result.get(timeout=10))
```

### 4. Vérifier les logs

```bash
# Logs worker
tail -f /var/log/celery/worker.log

# Logs beat
tail -f /var/log/celery/beat.log

# Logs Django
tail -f logs/auto_sync.log
```

## Gestion des tâches périodiques

### Via l'admin Django

1. Accéder à `/admin/`
2. Aller dans **Periodic Tasks**
3. Voir/modifier les tâches configurées dans `celery.py`

### Via le code

```python
from django_celery_beat.models import PeriodicTask, IntervalSchedule

# Créer un intervalle
schedule, _ = IntervalSchedule.objects.get_or_create(
    every=300,  # 5 minutes
    period=IntervalSchedule.SECONDS
)

# Créer une tâche périodique
PeriodicTask.objects.create(
    name='Monitor config 1',
    task='dhis_app.services.auto_sync.celery_tasks.celery_monitor_and_sync',
    interval=schedule,
    args=json.dumps([1]),  # config_id=1
    enabled=True
)
```

## Rollback (revenir aux threads)

Si nécessaire, pour revenir aux threads Python:

1. Arrêter Celery:
   ```bash
   sudo systemctl stop celery-worker celery-beat
   ```

2. Recommenter les lignes Celery dans `dhis_sync/__init__.py`

3. Revenir au cache local dans `settings.py`:
   ```python
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
           ...
       }
   }
   ```

4. Redémarrer Django:
   ```bash
   python manage.py runserver
   ```

## Performance et Tuning

### Augmenter le nombre de workers

```bash
celery -A dhis_sync worker --concurrency=4 --loglevel=info
```

### Créer des queues dédiées

Dans `celery.py`:

```python
app.conf.task_routes = {
    'dhis_app.services.auto_sync.celery_tasks.celery_trigger_auto_sync': {
        'queue': 'sync'
    },
    'dhis_app.services.auto_sync.celery_tasks.celery_monitor_*': {
        'queue': 'monitor'
    },
}
```

Démarrer des workers spécialisés:

```bash
# Worker pour les syncs (haute priorité)
celery -A dhis_sync worker -Q sync --concurrency=2

# Worker pour le monitoring
celery -A dhis_sync worker -Q monitor --concurrency=4
```

## Dépannage

### Redis ne démarre pas

```bash
sudo systemctl status redis
sudo systemctl restart redis
```

### Workers ne reçoivent pas les tâches

```bash
# Vérifier la connexion Redis
redis-cli ping

# Purger les tâches
celery -A dhis_sync purge
```

### Tâches bloquées

```bash
# Tuer les tâches actives
celery -A dhis_sync inspect active
celery -A dhis_sync control revoke <task_id>
```

### Voir les tâches échouées

Via Flower: `http://localhost:5555/tasks?state=FAILURE`

Ou dans Django admin: **Task Results**

## Support

Pour toute question sur la migration:
1. Consulter les logs Celery
2. Vérifier la documentation officielle: https://docs.celeryq.dev/
3. Tester les tâches individuellement avant de lancer en production

---

**Note**: La migration vers Celery est **optionnelle**. Le système actuel avec threads Python fonctionne bien pour le développement et les petites installations. Celery est recommandé pour la production à grande échelle.
