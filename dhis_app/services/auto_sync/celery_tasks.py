"""
Tâches Celery pour la synchronisation automatique

Ce fichier contient toutes les tâches Celery pour la production.
Pour activer, suivez le guide CELERY_MIGRATION.md
"""

import logging
import json
from celery import shared_task
from django.utils import timezone

from ...models import SyncConfiguration, AutoSyncSettings
from .change_detector import DHIS2ChangeDetector
from .lifecycle_manager import AutoSyncLifecycleManager
from .tasks import cleanup_dead_tasks

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def celery_trigger_auto_sync(self, sync_config_id: int, change_details: dict = None):
    """
    Tâche Celery pour déclencher une synchronisation automatique

    Args:
        sync_config_id: ID de la configuration
        change_details: Détails des changements détectés

    Returns:
        Résultat de la synchronisation
    """
    try:
        logger.info(f"[Celery] Démarrage sync pour config {sync_config_id}")

        sync_config = SyncConfiguration.objects.get(id=sync_config_id)
        lifecycle_manager = AutoSyncLifecycleManager(sync_config)

        result = lifecycle_manager.trigger_sync(change_details)

        if not result['success']:
            # Lever une exception pour déclencher le retry
            raise Exception(result.get('message', 'Synchronisation échouée'))

        logger.info(f"[Celery] Sync réussie pour config {sync_config_id}")
        return {
            'success': True,
            'config_id': sync_config_id,
            'result': result
        }

    except SyncConfiguration.DoesNotExist:
        logger.error(f"[Celery] Configuration {sync_config_id} introuvable")
        return {'success': False, 'error': 'Configuration introuvable'}

    except Exception as e:
        logger.error(f"[Celery] Erreur sync config {sync_config_id}: {e}", exc_info=True)

        # Retry avec backoff exponentiel
        retry_count = self.request.retries
        if retry_count < self.max_retries:
            countdown = 60 * (2 ** retry_count)  # 1min, 2min, 4min
            logger.info(f"[Celery] Retry {retry_count + 1}/{self.max_retries} dans {countdown}s")
            raise self.retry(exc=e, countdown=countdown)
        else:
            logger.error(f"[Celery] Max retries atteint pour config {sync_config_id}")
            return {'success': False, 'error': str(e), 'max_retries_reached': True}


@shared_task(bind=True)
def celery_monitor_and_sync(self, sync_config_id: int):
    """
    Tâche Celery pour monitorer et synchroniser une configuration

    Cette tâche:
    1. Vérifie si la synchronisation automatique est activée
    2. Détecte les changements sur l'instance source
    3. Déclenche une synchronisation si des changements sont détectés

    Args:
        sync_config_id: ID de la configuration

    Returns:
        Résultat du monitoring
    """
    try:
        logger.debug(f"[Celery] Monitoring config {sync_config_id}")

        sync_config = SyncConfiguration.objects.get(id=sync_config_id)
        auto_sync_settings = sync_config.auto_sync_settings

        if not auto_sync_settings.is_enabled:
            logger.debug(f"[Celery] Auto-sync désactivé pour config {sync_config_id}")
            return {'status': 'disabled', 'config_id': sync_config_id}

        # Vérifier si on peut synchroniser
        lifecycle_manager = AutoSyncLifecycleManager(sync_config)
        can_sync = lifecycle_manager.can_sync_now()

        if not can_sync['can_sync']:
            logger.debug(
                f"[Celery] Cannot sync config {sync_config_id}: {can_sync['reason']}"
            )
            return {
                'status': 'cannot_sync',
                'reason': can_sync['reason'],
                'config_id': sync_config_id
            }

        # Détecter les changements
        change_detector = DHIS2ChangeDetector(
            sync_config.source_instance,
            auto_sync_settings
        )
        changes = change_detector.detect_changes()

        # Si changements, déclencher la sync
        if changes['has_changes']:
            logger.info(
                f"[Celery] Changements détectés pour config {sync_config_id}, "
                f"déclenchement sync"
            )

            # Lancer la synchronisation de manière asynchrone
            celery_trigger_auto_sync.delay(sync_config_id, changes)

            return {
                'status': 'sync_triggered',
                'has_changes': True,
                'changes': changes,
                'config_id': sync_config_id
            }
        else:
            logger.debug(f"[Celery] Aucun changement pour config {sync_config_id}")
            return {
                'status': 'no_changes',
                'has_changes': False,
                'config_id': sync_config_id
            }

    except AutoSyncSettings.DoesNotExist:
        logger.warning(f"[Celery] Pas de settings auto-sync pour config {sync_config_id}")
        return {'status': 'no_settings', 'config_id': sync_config_id}

    except SyncConfiguration.DoesNotExist:
        logger.error(f"[Celery] Configuration {sync_config_id} introuvable")
        return {'status': 'not_found', 'config_id': sync_config_id}

    except Exception as e:
        logger.error(f"[Celery] Erreur monitoring config {sync_config_id}: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e), 'config_id': sync_config_id}


@shared_task
def celery_monitor_all_configs():
    """
    Tâche Celery pour monitorer toutes les configurations actives

    Cette tâche est exécutée périodiquement (via Celery Beat)
    pour lancer le monitoring de chaque configuration active.

    Returns:
        Résultat du monitoring de toutes les configs
    """
    try:
        logger.debug("[Celery] Monitoring de toutes les configurations")

        # Récupérer toutes les configs en mode automatique
        active_configs = SyncConfiguration.objects.filter(
            execution_mode='automatic',
            is_active=True
        ).select_related('auto_sync_settings')

        monitored = []
        skipped = []

        for config in active_configs:
            try:
                # Vérifier si activé
                auto_settings = config.auto_sync_settings
                if not auto_settings.is_enabled:
                    skipped.append(config.id)
                    continue

                # Lancer le monitoring de manière asynchrone
                celery_monitor_and_sync.delay(config.id)
                monitored.append(config.id)

            except AutoSyncSettings.DoesNotExist:
                logger.warning(f"[Celery] Pas de settings pour config {config.id}")
                skipped.append(config.id)

        logger.info(
            f"[Celery] Monitoring lancé: {len(monitored)} configs, "
            f"{len(skipped)} ignorées"
        )

        return {
            'status': 'success',
            'monitored': monitored,
            'skipped': skipped,
            'total': len(active_configs)
        }

    except Exception as e:
        logger.error(f"[Celery] Erreur monitoring toutes configs: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


@shared_task
def celery_cleanup_dead_tasks():
    """
    Tâche Celery pour nettoyer les tâches mortes

    Redémarre les threads morts si nécessaire.

    Returns:
        Résultat du nettoyage
    """
    try:
        logger.info("[Celery] Nettoyage des tâches mortes")
        result = cleanup_dead_tasks()
        logger.info(f"[Celery] Nettoyage terminé: {result}")
        return result

    except Exception as e:
        logger.error(f"[Celery] Erreur lors du nettoyage: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


@shared_task
def celery_health_check():
    """
    Tâche Celery pour vérifier la santé du système

    Vérifie:
    - Connexion aux instances DHIS2
    - État des configurations
    - Threads actifs

    Returns:
        Rapport de santé
    """
    try:
        logger.info("[Celery] Health check du système")

        from ...models import DHIS2Instance

        # Vérifier les instances
        instances = DHIS2Instance.objects.filter(is_active=True)
        instance_health = []

        for instance in instances:
            try:
                result = instance.test_connection()
                instance_health.append({
                    'id': instance.id,
                    'name': instance.name,
                    'healthy': result['success']
                })
            except Exception as e:
                instance_health.append({
                    'id': instance.id,
                    'name': instance.name,
                    'healthy': False,
                    'error': str(e)
                })

        # Vérifier les configs
        active_configs = SyncConfiguration.objects.filter(
            execution_mode='automatic',
            is_active=True
        ).count()

        # Récupérer les tâches actives
        from .tasks import get_active_sync_tasks
        tasks_info = get_active_sync_tasks()

        report = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'instances': {
                'total': len(instances),
                'healthy': sum(1 for i in instance_health if i['healthy']),
                'details': instance_health
            },
            'configurations': {
                'total_active': active_configs
            },
            'tasks': {
                'total_threads': tasks_info['total_sync_threads'],
                'active_configs': tasks_info['scheduler_status'].get('total_active', 0)
            }
        }

        logger.info(f"[Celery] Health check terminé: {report}")
        return report

    except Exception as e:
        logger.error(f"[Celery] Erreur health check: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def celery_schedule_sync(self, sync_config_id: int, scheduled_time: str):
    """
    Tâche Celery pour planifier une synchronisation à une heure spécifique

    Args:
        sync_config_id: ID de la configuration
        scheduled_time: Heure planifiée (ISO format)

    Returns:
        Résultat
    """
    try:
        logger.info(f"[Celery] Sync planifiée pour config {sync_config_id} à {scheduled_time}")

        # Déclencher la synchronisation
        result = celery_trigger_auto_sync.delay(sync_config_id)

        return {
            'status': 'scheduled',
            'config_id': sync_config_id,
            'scheduled_time': scheduled_time,
            'task_id': result.id
        }

    except Exception as e:
        logger.error(f"[Celery] Erreur planification sync: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}
