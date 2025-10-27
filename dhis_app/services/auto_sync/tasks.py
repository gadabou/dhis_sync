"""
Tâches asynchrones pour la synchronisation automatique

Ce module fournit des fonctions pour exécuter les synchronisations automatiques
en arrière-plan sans bloquer l'application principale.

Note: Ce module utilise threading pour l'instant. Si vous souhaitez utiliser Celery,
vous pouvez facilement adapter ces fonctions en tâches Celery.
"""

import logging
import threading
from typing import Optional, Dict, Any

from ...models import SyncConfiguration, AutoSyncSettings
from .scheduler import AutoSyncScheduler
from .lifecycle_manager import AutoSyncLifecycleManager

logger = logging.getLogger(__name__)


def trigger_auto_sync_async(sync_config_id: int, change_details: Optional[Dict[str, Any]] = None):
    """
    Déclenche une synchronisation automatique de manière asynchrone

    Args:
        sync_config_id: ID de la configuration de synchronisation
        change_details: Détails des changements détectés (optionnel)
    """
    def _run_sync():
        try:
            sync_config = SyncConfiguration.objects.get(id=sync_config_id)
            lifecycle_manager = AutoSyncLifecycleManager(sync_config)

            logger.info(f"Démarrage synchronisation async pour {sync_config.name}")
            result = lifecycle_manager.trigger_sync(change_details)

            if result['success']:
                logger.info(f"Synchronisation async réussie pour {sync_config.name}")
            else:
                logger.warning(f"Synchronisation async échouée: {result.get('message')}")

        except Exception as e:
            logger.error(f"Erreur dans la tâche async de synchronisation: {e}", exc_info=True)

    # Créer et démarrer le thread
    thread = threading.Thread(
        target=_run_sync,
        name=f"AsyncSync-{sync_config_id}",
        daemon=True
    )
    thread.start()

    return {
        'status': 'started',
        'thread_name': thread.name
    }


def start_auto_sync_monitoring_async(sync_config_id: Optional[int] = None):
    """
    Démarre le monitoring de synchronisation automatique de manière asynchrone

    Args:
        sync_config_id: ID de la configuration (None = toutes les configs actives)
    """
    def _start_monitoring():
        try:
            scheduler = AutoSyncScheduler.get_instance()
            scheduler.start(sync_config_id)
            logger.info(f"Monitoring auto-sync démarré pour config {sync_config_id or 'toutes'}")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du monitoring: {e}", exc_info=True)

    thread = threading.Thread(
        target=_start_monitoring,
        name="StartAutoSyncMonitoring",
        daemon=True
    )
    thread.start()

    return {
        'status': 'started',
        'config_id': sync_config_id
    }


def stop_auto_sync_monitoring_async(sync_config_id: Optional[int] = None):
    """
    Arrête le monitoring de synchronisation automatique

    Args:
        sync_config_id: ID de la configuration (None = toutes)
    """
    try:
        scheduler = AutoSyncScheduler.get_instance()
        scheduler.stop(sync_config_id)
        logger.info(f"Monitoring auto-sync arrêté pour config {sync_config_id or 'toutes'}")
        return {
            'status': 'stopped',
            'config_id': sync_config_id
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du monitoring: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }


# Si Celery est disponible, décommenter et adapter les tâches suivantes:
"""
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def celery_trigger_auto_sync(self, sync_config_id: int, change_details: Optional[Dict[str, Any]] = None):
    '''
    Tâche Celery pour déclencher une synchronisation automatique

    Args:
        sync_config_id: ID de la configuration
        change_details: Détails des changements
    '''
    try:
        sync_config = SyncConfiguration.objects.get(id=sync_config_id)
        lifecycle_manager = AutoSyncLifecycleManager(sync_config)

        result = lifecycle_manager.trigger_sync(change_details)

        if not result['success']:
            raise Exception(result.get('message', 'Synchronisation échouée'))

        return result

    except Exception as e:
        logger.error(f"Erreur dans la tâche Celery: {e}", exc_info=True)
        # Retry avec backoff exponentiel
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def celery_monitor_and_sync(sync_config_id: int):
    '''
    Tâche Celery périodique pour monitorer et synchroniser

    Args:
        sync_config_id: ID de la configuration
    '''
    try:
        from .change_detector import DHIS2ChangeDetector

        sync_config = SyncConfiguration.objects.get(id=sync_config_id)
        auto_sync_settings = sync_config.auto_sync_settings

        if not auto_sync_settings.is_enabled:
            return {'status': 'disabled'}

        # Détecter les changements
        change_detector = DHIS2ChangeDetector(
            sync_config.source_instance,
            auto_sync_settings
        )
        changes = change_detector.detect_changes()

        # Si changements, déclencher la sync
        if changes['has_changes']:
            celery_trigger_auto_sync.delay(sync_config_id, changes)

        return {'status': 'checked', 'has_changes': changes['has_changes']}

    except Exception as e:
        logger.error(f"Erreur dans le monitoring Celery: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}


@shared_task
def celery_start_all_auto_sync_monitoring():
    '''
    Démarre le monitoring pour toutes les configurations actives
    '''
    try:
        active_configs = SyncConfiguration.objects.filter(
            execution_mode='automatic',
            is_active=True
        ).select_related('auto_sync_settings')

        started = []
        for config in active_configs:
            try:
                if config.auto_sync_settings.is_enabled:
                    # Programmer la tâche périodique
                    from django_celery_beat.models import PeriodicTask, IntervalSchedule

                    schedule, _ = IntervalSchedule.objects.get_or_create(
                        every=config.auto_sync_settings.check_interval,
                        period=IntervalSchedule.SECONDS
                    )

                    PeriodicTask.objects.update_or_create(
                        name=f'auto_sync_monitor_{config.id}',
                        defaults={
                            'task': 'dhis_app.services.auto_sync.tasks.celery_monitor_and_sync',
                            'interval': schedule,
                            'args': json.dumps([config.id]),
                            'enabled': True
                        }
                    )
                    started.append(config.id)
            except Exception as e:
                logger.error(f"Erreur pour config {config.id}: {e}")

        return {'status': 'success', 'started_configs': started}

    except Exception as e:
        logger.error(f"Erreur lors du démarrage de tous les monitorings: {e}")
        return {'status': 'error', 'message': str(e)}
"""


# Fonctions utilitaires pour gérer les tâches en arrière-plan

def get_active_sync_tasks() -> Dict[str, Any]:
    """
    Retourne les informations sur les tâches de synchronisation actives

    Returns:
        Informations sur les tâches actives
    """
    scheduler = AutoSyncScheduler.get_instance()
    status = scheduler.get_status()

    # Compter les threads actifs
    active_threads = threading.enumerate()
    sync_threads = [
        t for t in active_threads
        if t.name.startswith('AutoSync-') or t.name.startswith('AsyncSync-')
    ]

    return {
        'scheduler_status': status,
        'total_sync_threads': len(sync_threads),
        'sync_threads': [
            {
                'name': t.name,
                'is_alive': t.is_alive(),
                'daemon': t.daemon
            }
            for t in sync_threads
        ]
    }


def cleanup_dead_tasks():
    """
    Nettoie les tâches mortes et redémarre si nécessaire

    Returns:
        Résultats du nettoyage
    """
    try:
        scheduler = AutoSyncScheduler.get_instance()
        status = scheduler.get_status()

        cleaned = []
        restarted = []

        # Parcourir toutes les configs actives
        active_configs = SyncConfiguration.objects.filter(
            execution_mode='automatic',
            is_active=True
        ).select_related('auto_sync_settings')

        for config in active_configs:
            try:
                auto_settings = config.auto_sync_settings
                if not auto_settings.is_enabled:
                    continue

                # Vérifier si le thread est mort
                if config.id in scheduler.threads:
                    thread = scheduler.threads[config.id]
                    if not thread.is_alive():
                        logger.warning(f"Thread mort détecté pour config {config.id}, redémarrage...")
                        scheduler.restart(config.id)
                        restarted.append(config.id)
                        cleaned.append(config.id)
                else:
                    # Aucun thread actif pour cette config, démarrer
                    logger.info(f"Démarrage du monitoring pour config {config.id}")
                    scheduler.start(config.id)
                    restarted.append(config.id)

            except Exception as e:
                logger.error(f"Erreur lors du nettoyage de la config {config.id}: {e}")

        return {
            'status': 'success',
            'cleaned': cleaned,
            'restarted': restarted,
            'total_active_after': len(scheduler.threads)
        }

    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des tâches: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }
