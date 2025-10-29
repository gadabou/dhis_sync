"""
Vues pour la gestion de la synchronisation automatique DHIS2
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt

from ..models import SyncConfiguration, AutoSyncSettings
from ..services.auto_sync import AutoSyncScheduler
from ..services.auto_sync.tasks import (
    get_active_sync_tasks,
    cleanup_dead_tasks,
    trigger_auto_sync_async
)

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def auto_sync_settings(request, config_id):
    """
    Page de configuration de la synchronisation automatique

    Args:
        config_id: ID de la configuration de synchronisation
    """
    sync_config = get_object_or_404(SyncConfiguration, id=config_id)

    # Récupérer ou créer les paramètres auto-sync
    try:
        auto_settings = sync_config.auto_sync_settings
    except AutoSyncSettings.DoesNotExist:
        auto_settings = AutoSyncSettings.objects.create(
            sync_config=sync_config,
            is_enabled=False
        )

    if request.method == 'POST':
        try:
            # Mettre à jour les paramètres
            auto_settings.is_enabled = request.POST.get('is_enabled') == 'on'
            auto_settings.check_interval = int(request.POST.get('check_interval', 300))
            auto_settings.immediate_sync = request.POST.get('immediate_sync') == 'on'
            auto_settings.delay_before_sync = int(request.POST.get('delay_before_sync', 30))

            auto_settings.monitor_metadata = request.POST.get('monitor_metadata') == 'on'
            auto_settings.monitor_data_values = request.POST.get('monitor_data_values') == 'on'

            auto_settings.max_sync_per_hour = int(request.POST.get('max_sync_per_hour', 10))
            auto_settings.cooldown_after_error = int(request.POST.get('cooldown_after_error', 1800))

            auto_settings.notify_on_change = request.POST.get('notify_on_change') == 'on'
            auto_settings.notify_on_sync_complete = request.POST.get('notify_on_sync_complete') == 'on'

            auto_settings.save()

            # Si activé et que la config est en mode automatique, démarrer le scheduler
            if auto_settings.is_enabled and sync_config.execution_mode == 'automatic':
                scheduler = AutoSyncScheduler.get_instance()
                scheduler.restart(config_id)
                messages.success(request, "Paramètres sauvegardés et synchronisation automatique démarrée")
            else:
                messages.success(request, "Paramètres de synchronisation automatique sauvegardés")

            return redirect('auto_sync_settings', config_id=config_id)

        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des paramètres: {e}", exc_info=True)
            messages.error(request, f"Erreur lors de la sauvegarde: {str(e)}")

    # Récupérer le statut du scheduler
    scheduler = AutoSyncScheduler.get_instance()
    scheduler_status = scheduler.get_status(config_id)

    context = {
        'sync_config': sync_config,
        'auto_settings': auto_settings,
        'scheduler_status': scheduler_status,
    }

    return render(request, 'dhis_app/auto_sync/settings.html', context)


@login_required
@require_POST
def start_auto_sync(request, config_id):
    """
    Démarre la synchronisation automatique pour une configuration

    Args:
        config_id: ID de la configuration
    """
    try:
        sync_config = get_object_or_404(SyncConfiguration, id=config_id)

        # Vérifier que la config est en mode automatique
        if sync_config.execution_mode != 'automatic':
            messages.warning(
                request,
                f"La configuration doit être en mode 'automatique'. Mode actuel: {sync_config.execution_mode}"
            )
            return redirect('auto_sync_settings', config_id=config_id)

        # Vérifier que les paramètres existent et sont activés
        try:
            auto_settings = sync_config.auto_sync_settings
            if not auto_settings.is_enabled:
                messages.warning(request, "La synchronisation automatique est désactivée dans les paramètres")
                return redirect('auto_sync_settings', config_id=config_id)
        except AutoSyncSettings.DoesNotExist:
            messages.error(request, "Paramètres de synchronisation automatique non configurés")
            return redirect('auto_sync_settings', config_id=config_id)

        # Démarrer le scheduler
        scheduler = AutoSyncScheduler.get_instance()
        scheduler.start(config_id)

        messages.success(request, f"Synchronisation automatique démarrée pour {sync_config.name}")
        logger.info(f"Auto-sync démarré pour config {config_id} par {request.user.username}")

        # Rediriger vers le dashboard pour voir la progression
        return redirect('auto_sync_dashboard')

    except Exception as e:
        logger.error(f"Erreur lors du démarrage de l'auto-sync: {e}", exc_info=True)
        messages.error(request, f"Erreur: {str(e)}")

    return redirect('auto_sync_settings', config_id=config_id)


@login_required
@require_POST
def stop_auto_sync(request, config_id):
    """
    Arrête la synchronisation automatique pour une configuration

    Args:
        config_id: ID de la configuration
    """
    try:
        sync_config = get_object_or_404(SyncConfiguration, id=config_id)

        scheduler = AutoSyncScheduler.get_instance()
        scheduler.stop(config_id)

        messages.success(request, f"Synchronisation automatique arrêtée pour {sync_config.name}")
        logger.info(f"Auto-sync arrêté pour config {config_id} par {request.user.username}")

    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt de l'auto-sync: {e}", exc_info=True)
        messages.error(request, f"Erreur: {str(e)}")

    return redirect('auto_sync_settings', config_id=config_id)


@login_required
@require_POST
def restart_auto_sync(request, config_id):
    """
    Redémarre la synchronisation automatique pour une configuration

    Args:
        config_id: ID de la configuration
    """
    try:
        sync_config = get_object_or_404(SyncConfiguration, id=config_id)

        scheduler = AutoSyncScheduler.get_instance()
        scheduler.restart(config_id)

        messages.success(request, f"Synchronisation automatique redémarrée pour {sync_config.name}")
        logger.info(f"Auto-sync redémarré pour config {config_id} par {request.user.username}")

    except Exception as e:
        logger.error(f"Erreur lors du redémarrage de l'auto-sync: {e}", exc_info=True)
        messages.error(request, f"Erreur: {str(e)}")

    return redirect('auto_sync_settings', config_id=config_id)


@login_required
@require_POST
def trigger_sync_now(request, config_id):
    """
    Déclenche une synchronisation immédiate (manuelle) en arrière-plan

    Args:
        config_id: ID de la configuration
    """
    try:
        sync_config = get_object_or_404(SyncConfiguration, id=config_id)

        # Déclencher la synchronisation en arrière-plan
        result = trigger_auto_sync_async(config_id)

        messages.success(
            request,
            f"Synchronisation déclenchée pour {sync_config.name}. "
            f"Thread: {result.get('thread_name')}"
        )
        logger.info(f"Sync manuelle déclenchée pour config {config_id} par {request.user.username}")

    except Exception as e:
        logger.error(f"Erreur lors du déclenchement de la sync: {e}", exc_info=True)
        messages.error(request, f"Erreur: {str(e)}")

    return redirect('auto_sync_settings', config_id=config_id)


@login_required
def auto_sync_dashboard(request):
    """
    Dashboard de la synchronisation automatique

    Affiche l'état de toutes les configurations en mode automatique
    """
    # Récupérer toutes les configurations actives en mode automatique
    auto_configs = SyncConfiguration.objects.filter(
        execution_mode='automatic',
        is_active=True
    ).select_related('source_instance', 'destination_instance')

    # Récupérer le statut du scheduler
    scheduler = AutoSyncScheduler.get_instance()
    scheduler_status = scheduler.get_status()

    # Récupérer les tâches actives
    active_tasks = get_active_sync_tasks()

    # Enrichir chaque config avec son statut
    configs_with_status = []
    for config in auto_configs:
        try:
            auto_settings = config.auto_sync_settings
            config_status = scheduler.get_status(config.id)

            configs_with_status.append({
                'config': config,
                'auto_settings': auto_settings,
                'scheduler_status': config_status,
                'is_running': config_status.get('is_running', False)
            })
        except AutoSyncSettings.DoesNotExist:
            configs_with_status.append({
                'config': config,
                'auto_settings': None,
                'scheduler_status': None,
                'is_running': False
            })

    context = {
        'configs_with_status': configs_with_status,
        'scheduler_status': scheduler_status,
        'active_tasks': active_tasks,
    }

    return render(request, 'dhis_app/auto_sync/dashboard.html', context)


# API endpoints (JSON)

@login_required
@require_http_methods(["GET"])
def api_auto_sync_status(request, config_id):
    """
    API: Retourne le statut de la synchronisation automatique

    Returns:
        JSON avec le statut
    """
    try:
        sync_config = get_object_or_404(SyncConfiguration, id=config_id)
        scheduler = AutoSyncScheduler.get_instance()
        status = scheduler.get_status(config_id)

        try:
            auto_settings = sync_config.auto_sync_settings
            settings_data = {
                'is_enabled': auto_settings.is_enabled,
                'check_interval': auto_settings.check_interval,
                'monitor_metadata': auto_settings.monitor_metadata,
                'monitor_data_values': auto_settings.monitor_data_values,
            }
        except AutoSyncSettings.DoesNotExist:
            settings_data = None

        return JsonResponse({
            'success': True,
            'config_id': config_id,
            'config_name': sync_config.name,
            'scheduler_status': status,
            'auto_settings': settings_data
        })

    except Exception as e:
        logger.error(f"Erreur API status: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_all_auto_sync_status(request):
    """
    API: Retourne le statut de toutes les synchronisations automatiques

    Returns:
        JSON avec tous les statuts
    """
    try:
        scheduler = AutoSyncScheduler.get_instance()
        global_status = scheduler.get_status()

        # Récupérer le détail de chaque config
        configs_status = []
        auto_configs = SyncConfiguration.objects.filter(
            execution_mode='automatic',
            is_active=True
        )

        for config in auto_configs:
            config_status = scheduler.get_status(config.id)
            try:
                auto_settings = config.auto_sync_settings
                is_enabled = auto_settings.is_enabled
            except AutoSyncSettings.DoesNotExist:
                is_enabled = False

            configs_status.append({
                'config_id': config.id,
                'config_name': config.name,
                'is_enabled': is_enabled,
                'is_running': config_status.get('is_running', False),
                'status': config_status
            })

        return JsonResponse({
            'success': True,
            'global_status': global_status,
            'configs': configs_status
        })

    except Exception as e:
        logger.error(f"Erreur API all status: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def api_cleanup_tasks(request):
    """
    API: Nettoie les tâches mortes et redémarre si nécessaire

    Returns:
        JSON avec les résultats
    """
    try:
        result = cleanup_dead_tasks()

        return JsonResponse({
            'success': True,
            'cleanup_result': result
        })

    except Exception as e:
        logger.error(f"Erreur API cleanup: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_sync_progress(request, config_id):
    """
    API: Retourne les statistiques de progression d'une synchronisation

    Returns:
        JSON avec les stats en temps réel
    """
    try:
        sync_config = get_object_or_404(SyncConfiguration, id=config_id)

        # Récupérer le dernier job en cours
        # IMPORTANT: Ne pas utiliser le cache ORM, forcer la récupération depuis la DB
        from ..models import SyncJob
        current_job = SyncJob.objects.filter(
            sync_config=sync_config,
            status='running'
        ).order_by('-created_at').first()

        if not current_job:
            # Pas de job en cours, récupérer le dernier terminé
            last_job = SyncJob.objects.filter(
                sync_config=sync_config
            ).order_by('-created_at').first()

            if last_job:
                return JsonResponse({
                    'success': True,
                    'is_running': False,
                    'last_job': {
                        'id': last_job.id,
                        'status': last_job.status,
                        'started_at': last_job.started_at.isoformat() if last_job.started_at else None,
                        'completed_at': last_job.completed_at.isoformat() if last_job.completed_at else None,
                        'total_synced': last_job.success_count or 0,
                        'total_errors': last_job.error_count or 0,
                        'error_message': last_job.last_error or '',
                    }
                })
            else:
                return JsonResponse({
                    'success': True,
                    'is_running': False,
                    'last_job': None
                })

        # FORCER le rafraîchissement depuis la base de données
        # Cela évite d'utiliser le cache ORM qui peut contenir des valeurs obsolètes
        current_job.refresh_from_db()

        # Calcul des statistiques pour le job en cours
        # Utiliser les champs disponibles dans le modèle
        total_items = current_job.total_items or 0
        processed_items = current_job.processed_items or 0
        success_count = current_job.success_count or 0
        error_count = current_job.error_count or 0

        # Calculer le pourcentage global
        # Si total_items est connu, utiliser le calcul précis
        # Sinon, utiliser le champ progress qui est mis à jour par l'orchestrateur
        if total_items > 0:
            progress_percent = int((processed_items / total_items) * 100)
        else:
            # Pour les syncs composites (metadata, etc), total_items n'est pas toujours connu d'avance
            # On utilise donc le champ progress qui est mis à jour manuellement par l'orchestrateur
            progress_percent = current_job.progress or 0

        # Calculer la vitesse (objets/seconde)
        if current_job.started_at:
            from django.utils import timezone as tz
            elapsed_seconds = (tz.now() - current_job.started_at).total_seconds()
            speed = processed_items / elapsed_seconds if elapsed_seconds > 0 else 0

            # Estimer le temps restant
            if speed > 0 and total_items > processed_items:
                remaining_items = total_items - processed_items
                estimated_seconds = remaining_items / speed
            else:
                estimated_seconds = 0
        else:
            speed = 0
            estimated_seconds = 0
            elapsed_seconds = 0

        # Déterminer l'étape actuelle
        current_step = 'En cours de synchronisation'
        if current_job.job_type == 'metadata':
            current_step = 'Synchronisation des métadonnées'
        elif current_job.job_type in ['data', 'aggregate', 'events', 'tracker', 'all_data']:
            current_step = 'Synchronisation des données'
        elif current_job.job_type == 'complete':
            if progress_percent < 50:
                current_step = 'Synchronisation des métadonnées'
            else:
                current_step = 'Synchronisation des données'

        return JsonResponse({
            'success': True,
            'is_running': True,
            'job_id': current_job.id,
            'config_name': sync_config.name,
            'progress': {
                'percent': progress_percent,
                'total_expected': total_items,
                'total_processed': processed_items,
                'total_synced': success_count,
                'total_errors': error_count,
            },
            'timing': {
                'started_at': current_job.started_at.isoformat() if current_job.started_at else None,
                'elapsed_seconds': int(elapsed_seconds),
                'speed_per_second': round(speed, 2),
                'estimated_remaining_seconds': int(estimated_seconds),
            },
            'resources': {},  # Pas de détail par ressource pour l'instant
            'current_step': current_step,
            'current_resource': current_job.get_job_type_display(),
        })

    except Exception as e:
        logger.error(f"Erreur API progress: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_dashboard_stats(request):
    """
    API: Retourne les statistiques globales du dashboard

    Returns:
        JSON avec toutes les stats pour le dashboard
    """
    try:
        from ..models import SyncJob
        scheduler = AutoSyncScheduler.get_instance()

        # Récupérer toutes les configs actives en mode automatique
        auto_configs = SyncConfiguration.objects.filter(
            execution_mode='automatic',
            is_active=True
        ).select_related('source_instance', 'destination_instance')

        configs_data = []
        for config in auto_configs:
            # Statut du scheduler
            scheduler_status = scheduler.get_status(config.id)

            # Settings
            try:
                auto_settings = config.auto_sync_settings
                settings_data = {
                    'is_enabled': auto_settings.is_enabled,
                    'check_interval': auto_settings.check_interval,
                }
            except AutoSyncSettings.DoesNotExist:
                settings_data = None

            # Dernier job - Récupérer depuis la DB directement
            last_job = SyncJob.objects.filter(
                sync_config=config
            ).order_by('-created_at').first()

            if last_job:
                # Rafraîchir depuis la DB pour avoir les dernières valeurs
                last_job.refresh_from_db()
                job_data = {
                    'id': last_job.id,
                    'status': last_job.status,
                    'started_at': last_job.started_at.isoformat() if last_job.started_at else None,
                    'completed_at': last_job.completed_at.isoformat() if last_job.completed_at else None,
                    'total_synced': last_job.success_count or 0,
                    'total_errors': last_job.error_count or 0,
                    'progress': last_job.progress or 0,
                    'processed_items': last_job.processed_items or 0,
                    'total_items': last_job.total_items or 0,
                }
            else:
                job_data = None

            # Job en cours - Récupérer depuis la DB directement
            current_job = SyncJob.objects.filter(
                sync_config=config,
                status='running'
            ).first()

            configs_data.append({
                'config_id': config.id,
                'config_name': config.name,
                'source': config.source_instance.name,
                'destination': config.destination_instance.name,
                'is_active': config.is_active,
                'is_running': scheduler_status.get('is_running', False),
                'settings': settings_data,
                'last_job': job_data,
                'has_running_job': current_job is not None,
            })

        return JsonResponse({
            'success': True,
            'configs': configs_data,
            'scheduler': scheduler.get_status(),
        })

    except Exception as e:
        logger.error(f"Erreur API dashboard stats: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
