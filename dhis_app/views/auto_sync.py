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
    # Récupérer toutes les configurations en mode automatique
    auto_configs = SyncConfiguration.objects.filter(
        execution_mode='automatic'
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
        auto_configs = SyncConfiguration.objects.filter(execution_mode='automatic')

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
