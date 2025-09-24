from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
import logging

from ..models import SyncConfiguration
from ..services.sync_orchestrator import SyncOrchestrator

logger = logging.getLogger(__name__)


class LaunchSynchronizationView(LoginRequiredMixin, View):
    """Vue pour lancer une synchronisation manuelle"""

    def get_config(self, config_id):
        """Récupère la configuration de synchronisation"""
        return get_object_or_404(SyncConfiguration, id=config_id)

    def validate_config(self, config):
        """Valide que la configuration peut être utilisée"""
        if not config.is_active:
            return 'La configuration doit être active pour lancer une synchronisation'

        # Vérifier qu'aucun job n'est en cours pour cette configuration
        running_jobs = config.jobs.filter(status__in=['pending', 'running']).exists()
        if running_jobs:
            return 'Une synchronisation est déjà en cours pour cette configuration'

        return None

    def handle_error(self, request, error_message, config_id):
        """Gère les erreurs et retourne la réponse appropriée"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_message
            })

        messages.error(request, error_message)
        return redirect('sync_config_detail', config_id=config_id)

    def handle_success(self, request, success_message, job_id):
        """Gère le succès et retourne la réponse appropriée"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': success_message,
                'job_id': job_id,
                'redirect': reverse('sync_job_detail', kwargs={'job_id': job_id})
            })

        messages.success(request, success_message)
        return redirect('sync_job_detail', job_id=job_id)

    def post(self, request, config_id):
        config = self.get_config(config_id)

        # Validation
        error_message = self.validate_config(config)
        if error_message:
            return self.handle_error(request, error_message, config.id)

        try:
            # Récupérer les paramètres de synchronisation
            sync_data = request.POST

            # Types de synchronisation à effectuer
            sync_types = sync_data.getlist('sync_types')
            if not sync_types:
                # Par défaut, synchronisation selon le type de configuration
                if config.sync_type == 'metadata':
                    sync_types = ['metadata']
                elif config.sync_type == 'data':
                    sync_types = ['tracker', 'events', 'aggregate']
                else:  # complete
                    sync_types = ['metadata', 'tracker', 'events', 'aggregate']

            # Paramètres optionnels
            metadata_families = sync_data.getlist('metadata_families') or None
            org_units = sync_data.getlist('org_units') or None
            programs = sync_data.getlist('programs') or None
            periods = sync_data.getlist('periods') or None

            # Créer l'orchestrateur
            orchestrator = SyncOrchestrator(
                source_instance=config.source_instance,
                destination_instance=config.destination_instance
            )

            # Lancer la synchronisation
            job = orchestrator.execute_full_sync(
                sync_config=config,
                sync_types=sync_types,
                metadata_families=metadata_families,
                org_units=org_units,
                programs=programs,
                periods=periods
            )

            success_message = f'Synchronisation lancée avec succès (Job #{job.id})'
            return self.handle_success(request, success_message, job.id)

        except Exception as e:
            logger.error(f"Erreur lors du lancement de la synchronisation: {e}")
            error_message = f'Erreur lors du lancement: {str(e)}'
            return self.handle_error(request, error_message, config.id)

    def get(self, request, config_id):
        return redirect('sync_config_detail', config_id=config_id)


class LaunchMetadataSyncView(LaunchSynchronizationView):
    """Vue pour lancer uniquement la synchronisation des métadonnées"""

    def post(self, request, config_id):
        config = self.get_config(config_id)

        # Validation
        error_message = self.validate_config(config)
        if error_message:
            return self.handle_error(request, error_message, config.id)

        try:
            # Paramètres
            families = request.POST.getlist('metadata_families') or None

            # Créer l'orchestrateur et lancer la synchronisation
            orchestrator = SyncOrchestrator(
                source_instance=config.source_instance,
                destination_instance=config.destination_instance
            )

            job = orchestrator.execute_metadata_sync(
                sync_config=config,
                families=families
            )

            success_message = f'Synchronisation des métadonnées lancée (Job #{job.id})'
            return self.handle_success(request, success_message, job.id)

        except Exception as e:
            logger.error(f"Erreur lors du lancement de la synchronisation métadonnées: {e}")
            error_message = f'Erreur lors du lancement: {str(e)}'
            return self.handle_error(request, error_message, config.id)


class LaunchDataSyncView(LaunchSynchronizationView):
    """Vue pour lancer uniquement la synchronisation des données"""

    def post(self, request, config_id):
        config = self.get_config(config_id)

        # Validation
        error_message = self.validate_config(config)
        if error_message:
            return self.handle_error(request, error_message, config.id)

        try:
            # Paramètres
            sync_types = request.POST.getlist('data_types')
            if not sync_types:
                sync_types = ['tracker', 'events', 'aggregate']  # Par défaut tous

            org_units = request.POST.getlist('org_units') or None
            programs = request.POST.getlist('programs') or None
            periods = request.POST.getlist('periods') or None

            # Créer l'orchestrateur et lancer la synchronisation
            orchestrator = SyncOrchestrator(
                source_instance=config.source_instance,
                destination_instance=config.destination_instance
            )

            job = orchestrator.execute_data_sync(
                sync_config=config,
                sync_types=sync_types,
                org_units=org_units,
                programs=programs,
                periods=periods
            )

            success_message = f'Synchronisation des données lancée (Job #{job.id})'
            return self.handle_success(request, success_message, job.id)

        except Exception as e:
            logger.error(f"Erreur lors du lancement de la synchronisation données: {e}")
            error_message = f'Erreur lors du lancement: {str(e)}'
            return self.handle_error(request, error_message, config.id)


class GetSyncParametersView(LoginRequiredMixin, View):
    """Vue pour récupérer les paramètres disponibles pour la synchronisation"""

    def get(self, request, config_id):
        config = get_object_or_404(SyncConfiguration, id=config_id)

        try:
            # Créer l'orchestrateur pour accéder aux services
            orchestrator = SyncOrchestrator(
                source_instance=config.source_instance,
                destination_instance=config.destination_instance
            )

            parameters = {
                'metadata_families': [],
                'org_units': [],
                'programs': [],
                'data_elements': []
            }

            # Récupérer les familles de métadonnées disponibles
            try:
                families = orchestrator.metadata_service.get_available_families()
                parameters['metadata_families'] = [
                    {'id': family_id, 'name': family_config['description']}
                    for family_id, family_config in families.items()
                ]
            except Exception as e:
                logger.warning(f"Erreur récupération familles métadonnées: {e}")

            # Récupérer les unités d'organisation
            try:
                orgunits = config.source_instance.get_metadata(
                    'organisationUnits',
                    fields='id,name,level',
                    paging=False
                )
                parameters['org_units'] = [
                    {
                        'id': ou.get('id'),
                        'name': ou.get('name'),
                        'level': ou.get('level', 0)
                    }
                    for ou in orgunits[:100]  # Limiter à 100 pour éviter surcharge
                ]
                # Trier par niveau puis par nom
                parameters['org_units'].sort(key=lambda x: (x['level'], x['name']))

            except Exception as e:
                logger.warning(f"Erreur récupération unités d'organisation: {e}")

            # Récupérer les programmes
            try:
                programs = config.source_instance.get_metadata(
                    'programs',
                    fields='id,name,programType',
                    paging=False
                )
                parameters['programs'] = [
                    {
                        'id': prog.get('id'),
                        'name': prog.get('name'),
                        'type': prog.get('programType')
                    }
                    for prog in programs
                ]
                parameters['programs'].sort(key=lambda x: x['name'])

            except Exception as e:
                logger.warning(f"Erreur récupération programmes: {e}")

            return JsonResponse({
                'success': True,
                'parameters': parameters
            })

        except Exception as e:
            logger.error(f"Erreur récupération paramètres sync: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            })

    def post(self, request, config_id):
        return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})
