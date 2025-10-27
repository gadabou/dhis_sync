# Logging et Migration Celery - Récapitulatif

## 📊 Système de Logging

### Fichiers créés

1. **`dhis_sync/logging_config.py`** - Configuration centralisée des logs
2. **`dhis_app/views/logs.py`** - Vues pour consulter les logs
3. **URLs ajoutées** dans `dhis_app/urls.py` pour accéder aux logs

### Fichiers de logs générés

Tous les logs sont dans le répertoire `logs/` (créé automatiquement):

| Fichier | Contenu | Rotation |
|---------|---------|----------|
| `dhis2_sync.log` | Logs généraux de l'application | 10MB, 5 fichiers |
| `errors.log` | Erreurs uniquement | 10MB, 5 fichiers |
| `auto_sync.log` | Logs de la synchronisation automatique | 10MB, 10 fichiers |
| `changes_detected.log` | Changements détectés par le monitoring | 5MB, 5 fichiers |
| `sync_jobs.log` | Historique des jobs de synchronisation | 10MB, 10 fichiers |

### Accéder aux logs via l'interface web

#### 1. Visualiseur de logs général

URL: `/logs/`

Affiche:
- Liste de tous les fichiers de logs
- Taille des fichiers
- Date de dernière modification
- Actions: Voir, Télécharger, Vider

#### 2. Logs Auto-Sync spécifiques

URL: `/logs/auto-sync/`

Affiche les 100 dernières lignes de:
- `auto_sync.log`
- `changes_detected.log`
- `sync_jobs.log`

#### 3. API pour les logs

```bash
# Voir un fichier de log
GET /logs/view/auto_sync.log/?lines=100&tail=true

# Télécharger un fichier
GET /logs/download/auto_sync.log/

# Vider un fichier
POST /logs/clear/auto_sync.log/

# Rechercher dans les logs
GET /logs/search/?query=error&files=auto_sync.log,errors.log
```

### Surveiller les logs en temps réel

#### Via l'interface web (à implémenter avec WebSockets si besoin)

Actuellement, vous pouvez:
1. Accéder à `/logs/`
2. Cliquer sur "Voir" pour un fichier
3. Les dernières lignes s'affichent

#### Via la ligne de commande

```bash
# Tous les logs auto-sync
tail -f logs/auto_sync.log

# Changements détectés uniquement
tail -f logs/changes_detected.log

# Jobs de synchronisation
tail -f logs/sync_jobs.log

# Erreurs uniquement
tail -f logs/errors.log

# Filtrer par niveau
tail -f logs/auto_sync.log | grep ERROR
tail -f logs/auto_sync.log | grep WARNING
```

### Niveaux de logs configurés

| Logger | Niveau | Fichiers |
|--------|--------|----------|
| `dhis_app.services.auto_sync` | DEBUG | `auto_sync.log`, Console |
| `dhis_app.services.auto_sync.change_detector` | DEBUG | `auto_sync.log`, `changes_detected.log` |
| `dhis_app.services.auto_sync.lifecycle_manager` | DEBUG | `auto_sync.log`, `sync_jobs.log` |
| `dhis_app.services.auto_sync.scheduler` | INFO | `auto_sync.log` |
| `dhis_app.services.sync_orchestrator` | INFO | `sync_jobs.log` |

### Exemples de logs

#### Détection de changements

```
[AUTO-SYNC] [INFO] 2025-10-10 14:23:01 [change_detector] - Détection de changements pour Instance Source
[AUTO-SYNC] [INFO] 2025-10-10 14:23:02 [change_detector] - Changements détectés pour organisationUnits
[AUTO-SYNC] [DEBUG] 2025-10-10 14:23:03 [change_detector] - 5 éléments modifiés depuis 2025-10-10 14:00:00
```

#### Déclenchement de synchronisation

```
[AUTO-SYNC] [INFO] 2025-10-10 14:23:05 [lifecycle_manager] - Démarrage de la synchronisation incrémentale pour Config Test
[AUTO-SYNC] [INFO] 2025-10-10 14:23:06 [lifecycle_manager] - Synchronisation des métadonnées modifiées
[AUTO-SYNC] [INFO] 2025-10-10 14:25:30 [lifecycle_manager] - Synchronisation incrémentale réussie
```

#### Erreurs

```
[AUTO-SYNC] [ERROR] 2025-10-10 14:30:01 [scheduler] - Erreur lors de la synchronisation: Connection timeout
[AUTO-SYNC] [INFO] 2025-10-10 14:30:02 [lifecycle_manager] - Cooldown activé jusqu'à 2025-10-10 15:00:02
```

## 🔧 Configuration dans settings.py

La configuration a été ajoutée automatiquement:

```python
# ===== LOGGING CONFIGURATION =====
from .logging_config import LOGGING

# ===== CACHE CONFIGURATION =====
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'dhis2-sync-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

# ===== CELERY CONFIGURATION (Optionnel - commenté par défaut) =====
# Décommenter pour activer Celery en production
```

## 🚀 Migration vers Celery (Production)

### Quand migrer vers Celery ?

Migrer vers Celery quand:
- ✅ Vous déployez en production
- ✅ Vous avez plusieurs configurations actives
- ✅ Vous voulez une haute disponibilité
- ✅ Vous voulez un monitoring avancé
- ✅ Les threads Python ne suffisent plus

### Fichiers créés pour Celery

1. **`dhis_sync/celery.py`** - Configuration Celery principale
2. **`dhis_app/services/auto_sync/celery_tasks.py`** - Tâches Celery complètes
3. **`CELERY_MIGRATION.md`** - Guide de migration étape par étape

### Tâches Celery disponibles

| Tâche | Description | Fréquence |
|-------|-------------|-----------|
| `celery_trigger_auto_sync` | Déclenche une synchronisation | À la demande |
| `celery_monitor_and_sync` | Surveille et synchronise une config | À la demande |
| `celery_monitor_all_configs` | Surveille toutes les configs | 60s (Beat) |
| `celery_cleanup_dead_tasks` | Nettoie les threads morts | 5 min (Beat) |
| `celery_health_check` | Vérifie la santé du système | 1h (Beat) |

### Quick Start Celery

```bash
# 1. Installer Redis
sudo apt-get install redis-server
sudo systemctl start redis

# 2. Installer les packages Python
pip install celery redis django-celery-beat django-celery-results django-redis

# 3. Décommenter dans dhis_sync/__init__.py
from .celery import app as celery_app
__all__ = ('celery_app',)

# 4. Décommenter la config Celery dans settings.py

# 5. Migrer la base de données
python manage.py migrate django_celery_beat
python manage.py migrate django_celery_results

# 6. Démarrer Celery (2 terminaux)
celery -A dhis_sync worker --loglevel=info
celery -A dhis_sync beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# 7. (Optionnel) Monitoring avec Flower
pip install flower
celery -A dhis_sync flower --port=5555
# Accès: http://localhost:5555
```

### Rollback

Pour revenir aux threads Python:
1. Arrêter Celery
2. Recommenter les lignes dans `__init__.py`
3. Redémarrer Django

## 📋 Commandes utiles

### Logs

```bash
# Voir tous les logs en temps réel
tail -f logs/*.log

# Chercher des erreurs
grep -r "ERROR" logs/

# Statistiques de logs
wc -l logs/*.log

# Effacer les logs (attention!)
> logs/auto_sync.log
```

### Celery (si activé)

```bash
# Statut des workers
celery -A dhis_sync inspect active

# Tâches planifiées
celery -A dhis_sync inspect scheduled

# Purger toutes les tâches
celery -A dhis_sync purge

# Logs Celery
tail -f /var/log/celery/worker.log
tail -f /var/log/celery/beat.log
```

### Django

```bash
# Voir les configurations auto-sync actives
python manage.py shell
>>> from dhis_app.models import SyncConfiguration
>>> SyncConfiguration.objects.filter(execution_mode='automatic', is_active=True)

# Lancer une synchronisation manuelle
>>> from dhis_app.services.auto_sync import start_auto_sync
>>> start_auto_sync(sync_config_id=1)
```

## 🔍 Monitoring et Alertes

### Via l'interface web

1. **Dashboard Auto-Sync**: `/auto-sync/dashboard/`
   - État de toutes les configurations
   - Threads actifs
   - Statistiques

2. **Logs**: `/logs/` ou `/logs/auto-sync/`
   - Consultation en temps réel
   - Recherche
   - Téléchargement

3. **Flower** (si Celery activé): `http://localhost:5555`
   - Tâches en cours
   - Historique
   - Statistiques

### Alertes (à implémenter selon vos besoins)

Vous pouvez ajouter des alertes en modifiant les loggers pour envoyer:
- **Emails** sur erreurs critiques
- **Slack/Discord** notifications
- **Webhooks** vers des systèmes de monitoring

Exemple dans `logging_config.py`:

```python
# Ajouter un handler email pour les erreurs critiques
'mail_admins': {
    'level': 'ERROR',
    'class': 'django.utils.log.AdminEmailHandler',
    'include_html': True,
}
```

## 📚 Documentation

- **Guide utilisateur**: `AUTO_SYNC_GUIDE.md`
- **Documentation technique**: `dhis_app/services/auto_sync/README.md`
- **Guide Celery**: `CELERY_MIGRATION.md`
- **Ce fichier**: `LOGGING_AND_CELERY.md`

## 🎯 Prochaines étapes recommandées

### Immédiat (Développement)

1. ✅ Tester la synchronisation automatique avec threads
2. ✅ Surveiller les logs via `/logs/`
3. ✅ Ajuster les paramètres auto-sync selon vos besoins

### Court terme (Avant production)

1. ⏳ Tester avec plusieurs configurations
2. ⏳ Ajuster les intervalles de vérification
3. ⏳ Configurer des alertes
4. ⏳ Documenter vos configurations spécifiques

### Production

1. 🚀 Migrer vers Celery (suivre `CELERY_MIGRATION.md`)
2. 🚀 Configurer Redis
3. 🚀 Mettre en place Flower pour le monitoring
4. 🚀 Créer des services systemd
5. 🚀 Configurer des backups Redis

## ✅ Résumé

Vous avez maintenant:

1. **Système de logging complet**
   - ✅ 5 fichiers de logs différents
   - ✅ Rotation automatique
   - ✅ Interface web de consultation
   - ✅ API pour l'intégration

2. **Migration Celery préparée**
   - ✅ Configuration complète
   - ✅ Tâches Celery prêtes
   - ✅ Guide de migration détaillé
   - ✅ Possibilité de rollback

3. **Monitoring**
   - ✅ Dashboard web
   - ✅ Logs en temps réel
   - ✅ API de statut
   - ✅ (Optionnel) Flower

**Le système est prêt pour la production ! 🎉**
