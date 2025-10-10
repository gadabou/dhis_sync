"""
Configuration Celery pour DHIS2 Sync

Ce fichier configure Celery pour l'exécution des tâches asynchrones
en production. Pour activer Celery, suivez le guide CELERY_MIGRATION.md
"""

import os
from celery import Celery
from celery.schedules import crontab

# Définir le module de settings Django par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dhis_sync.settings')

# Créer l'application Celery
app = Celery('dhis_sync')

# Charger la configuration depuis Django settings avec le namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tâches dans les applications Django
app.autodiscover_tasks()


# Configuration des tâches périodiques (Celery Beat)
app.conf.beat_schedule = {
    # Tâche pour monitorer et synchroniser toutes les configurations actives
    'monitor-all-auto-sync-configs': {
        'task': 'dhis_app.services.auto_sync.tasks.celery_monitor_all_configs',
        'schedule': 60.0,  # Toutes les 60 secondes
        'options': {
            'expires': 55.0,  # Expire après 55 secondes
        }
    },

    # Nettoyer les tâches mortes toutes les 5 minutes
    'cleanup-dead-tasks': {
        'task': 'dhis_app.services.auto_sync.tasks.celery_cleanup_dead_tasks',
        'schedule': crontab(minute='*/5'),  # Toutes les 5 minutes
    },

    # Vérifier la santé du système toutes les heures
    'health-check': {
        'task': 'dhis_app.services.auto_sync.tasks.celery_health_check',
        'schedule': crontab(minute=0),  # Toutes les heures
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tâche de debug pour tester Celery"""
    print(f'Request: {self.request!r}')
