"""
Service principal d'orchestration des synchronisations DHIS2
"""
import logging
from typing import Dict, List, Any, Optional
from django.utils import timezone
from ..models import SyncJob, SyncConfiguration, DHIS2Instance
from .metadata.metadata_sync_service import MetadataSyncService
from .data.tracker import TrackerDataService
from .data.events import EventsDataService
from .data.aggregate import AggregateDataService

logger = logging.getLogger(__name__)


class SyncOrchestratorError(Exception):
    """Exception personnalisée pour l'orchestrateur de synchronisation"""
    pass


class SyncOrchestrator:
    """
    Service principal d'orchestration des synchronisations DHIS2
    Gère l'ordre de synchronisation: métadonnées → tracker → events → agrégées
    """

    def __init__(self, sync_config: SyncConfiguration):
        """
        Initialise l'orchestrateur de synchronisation

        Args:
            sync_config: Configuration de synchronisation contenant les instances source et destination
        """
        self.sync_config = sync_config
        self.source_instance = sync_config.source_instance
        self.destination_instance = sync_config.destination_instance
        self.logger = logger

        # Initialiser les services
        self.metadata_service = MetadataSyncService(sync_config)
        self.tracker_service = TrackerDataService(sync_config)
        self.events_service = EventsDataService(sync_config)
        self.aggregate_service = AggregateDataService(sync_config)

    def execute_full_sync(self, sync_config: SyncConfiguration,
                         sync_types: Optional[List[str]] = None,
                         metadata_families: Optional[List[str]] = None,
                         org_units: Optional[List[str]] = None,
                         programs: Optional[List[str]] = None,
                         periods: Optional[List[str]] = None) -> SyncJob:
        """
        Exécute une synchronisation complète selon l'ordre défini

        Args:
            sync_config: Configuration de synchronisation
            sync_types: Types de synchronisation à effectuer (metadata, tracker, events, aggregate)
            metadata_families: Familles de métadonnées à synchroniser
            org_units: Unités d'organisation à synchroniser
            programs: Programmes à synchroniser
            periods: Périodes à synchroniser

        Returns:
            Job de synchronisation créé
        """
        # Types par défaut si non spécifiés
        if sync_types is None:
            sync_types = ['metadata', 'tracker', 'events', 'aggregate']

        # Créer le job de synchronisation
        job = SyncJob.objects.create(
            sync_config=sync_config,
            job_type='complete',
            status='pending',
            log_message="=== DÉBUT SYNCHRONISATION COMPLÈTE ===\n"
        )

        try:
            job.status = 'running'
            job.started_at = timezone.now()
            job.log_message += f"Types de synchronisation: {', '.join(sync_types)}\n"
            job.log_message += f"Source: {self.source_instance.name}\n"
            job.log_message += f"Destination: {self.destination_instance.name}\n"
            job.save()

            # Vérifier la compatibilité globale
            compatibility = self._check_global_compatibility()
            if not compatibility['compatible']:
                error_msg = "Incompatibilité détectée: " + "; ".join(compatibility['errors'])
                job.status = 'failed'
                job.log_message += f"ERREUR: {error_msg}\n"
                job.completed_at = timezone.now()
                job.save()
                return job

            # Exécuter les synchronisations dans l'ordre
            sync_results = {}
            total_progress_steps = len(sync_types)
            current_step = 0

            # 1. MÉTADONNÉES (si demandées)
            if 'metadata' in sync_types:
                current_step += 1
                job.log_message += f"\n{'='*50}\n"
                job.log_message += f"ÉTAPE {current_step}/{total_progress_steps}: SYNCHRONISATION MÉTADONNÉES\n"
                job.log_message += f"{'='*50}\n"
                job.save()

                metadata_result = self.metadata_service.sync_all_metadata(
                    job=job,
                    families=metadata_families
                )
                sync_results['metadata'] = metadata_result

                # Mettre à jour le progrès global
                job.progress = int((current_step / total_progress_steps) * 100)
                job.save()

                if not metadata_result['success']:
                    job.log_message += "AVERTISSEMENT: Erreurs dans la synchronisation des métadonnées\n"
                    job.save()

            # 2. DONNÉES TRACKER (si demandées)
            if 'tracker' in sync_types:
                current_step += 1
                job.log_message += f"\n{'='*50}\n"
                job.log_message += f"ÉTAPE {current_step}/{total_progress_steps}: SYNCHRONISATION TRACKER\n"
                job.log_message += f"{'='*50}\n"
                job.save()

                tracker_result = self.tracker_service.sync_tracker_data(
                    job=job,
                    programs=programs,
                    org_units=org_units
                )
                sync_results['tracker'] = tracker_result

                # Mettre à jour le progrès global
                job.progress = int((current_step / total_progress_steps) * 100)
                job.save()

                if not tracker_result['success']:
                    job.log_message += "AVERTISSEMENT: Erreurs dans la synchronisation tracker\n"
                    job.save()

            # 3. DONNÉES ÉVÉNEMENTS (si demandées)
            if 'events' in sync_types:
                current_step += 1
                job.log_message += f"\n{'='*50}\n"
                job.log_message += f"ÉTAPE {current_step}/{total_progress_steps}: SYNCHRONISATION ÉVÉNEMENTS\n"
                job.log_message += f"{'='*50}\n"
                job.save()

                events_result = self.events_service.sync_events_data(
                    job=job,
                    programs=programs,
                    org_units=org_units
                )
                sync_results['events'] = events_result

                # Mettre à jour le progrès global
                job.progress = int((current_step / total_progress_steps) * 100)
                job.save()

                if not events_result['success']:
                    job.log_message += "AVERTISSEMENT: Erreurs dans la synchronisation des événements\n"
                    job.save()

            # 4. DONNÉES AGRÉGÉES (si demandées)
            if 'aggregate' in sync_types:
                current_step += 1
                job.log_message += f"\n{'='*50}\n"
                job.log_message += f"ÉTAPE {current_step}/{total_progress_steps}: SYNCHRONISATION DONNÉES AGRÉGÉES\n"
                job.log_message += f"{'='*50}\n"
                job.save()

                aggregate_result = self.aggregate_service.sync_aggregate_data(
                    job=job,
                    org_units=org_units,
                    periods=periods
                )
                sync_results['aggregate'] = aggregate_result

                # Mettre à jour le progrès global
                job.progress = 100
                job.save()

                if not aggregate_result['success']:
                    job.log_message += "AVERTISSEMENT: Erreurs dans la synchronisation des données agrégées\n"
                    job.save()

            # Finaliser le job
            job.completed_at = timezone.now()
            job.progress = 100

            # Déterminer le statut final
            all_successful = all(result.get('success', False) for result in sync_results.values())
            has_errors = any(not result.get('success', False) for result in sync_results.values())

            if all_successful:
                job.status = 'completed'
                job.log_message += f"\n{'='*60}\n"
                job.log_message += "🎉 SYNCHRONISATION COMPLÈTE RÉUSSIE\n"
                job.log_message += f"{'='*60}\n"
            elif has_errors:
                job.status = 'completed_with_warnings'
                job.log_message += f"\n{'='*60}\n"
                job.log_message += "⚠️  SYNCHRONISATION TERMINÉE AVEC AVERTISSEMENTS\n"
                job.log_message += f"{'='*60}\n"
            else:
                job.status = 'failed'
                job.log_message += f"\n{'='*60}\n"
                job.log_message += "❌ SYNCHRONISATION ÉCHOUÉE\n"
                job.log_message += f"{'='*60}\n"

            # Ajouter un résumé
            job.log_message += self._generate_sync_summary(sync_results)
            job.save()

            return job

        except Exception as e:
            error_msg = f"Erreur critique lors de la synchronisation: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            job.status = 'failed'
            job.completed_at = timezone.now()
            job.log_message += f"\nERRRUR CRITIQUE: {error_msg}\n"
            job.save()

            return job

    def execute_metadata_sync(self, sync_config: SyncConfiguration,
                             families: Optional[List[str]] = None) -> SyncJob:
        """
        Exécute uniquement la synchronisation des métadonnées

        Args:
            sync_config: Configuration de synchronisation
            families: Familles de métadonnées à synchroniser

        Returns:
            Job de synchronisation créé
        """
        job = SyncJob.objects.create(
            sync_config=sync_config,
            job_type='metadata',
            status='pending',
            log_message="=== SYNCHRONISATION MÉTADONNÉES SEULEMENT ===\n"
        )

        try:
            result = self.metadata_service.sync_all_metadata(job=job, families=families)
            return job

        except Exception as e:
            error_msg = f"Erreur critique lors de la synchronisation des métadonnées: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            job.status = 'failed'
            job.completed_at = timezone.now()
            job.log_message += f"\nERREUR CRITIQUE: {error_msg}\n"
            job.save()

            return job

    def execute_data_sync(self, sync_config: SyncConfiguration,
                         sync_types: List[str],
                         org_units: Optional[List[str]] = None,
                         programs: Optional[List[str]] = None,
                         periods: Optional[List[str]] = None) -> SyncJob:
        """
        Exécute uniquement la synchronisation des données

        Args:
            sync_config: Configuration de synchronisation
            sync_types: Types de données à synchroniser (tracker, events, aggregate)
            org_units: Unités d'organisation à synchroniser
            programs: Programmes à synchroniser
            periods: Périodes à synchroniser

        Returns:
            Job de synchronisation créé
        """
        job = SyncJob.objects.create(
            sync_config=sync_config,
            job_type='data',
            status='pending',
            log_message="=== SYNCHRONISATION DONNÉES SEULEMENT ===\n"
        )

        try:
            return self.execute_full_sync(
                sync_config=sync_config,
                sync_types=sync_types,
                org_units=org_units,
                programs=programs,
                periods=periods
            )

        except Exception as e:
            error_msg = f"Erreur critique lors de la synchronisation des données: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            job.status = 'failed'
            job.completed_at = timezone.now()
            job.log_message += f"\nERREUR CRITIQUE: {error_msg}\n"
            job.save()

            return job

    def _check_global_compatibility(self) -> Dict[str, Any]:
        """
        Vérifie la compatibilité globale des instances pour tous les services

        Returns:
            Résultat de vérification de compatibilité
        """
        try:
            # Utiliser le service de métadonnées pour la vérification globale
            compatibility = self.metadata_service.check_instances_compatibility()

            # Ajouter des vérifications spécifiques si nécessaire
            # Par exemple, vérifier les versions DHIS2, les permissions, etc.

            return compatibility

        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de compatibilité: {e}")
            return {
                'compatible': False,
                'errors': [str(e)]
            }

    def _generate_sync_summary(self, sync_results: Dict[str, Dict[str, Any]]) -> str:
        """
        Génère un résumé de la synchronisation

        Args:
            sync_results: Résultats de synchronisation

        Returns:
            Résumé formaté
        """
        summary = "\n📊 RÉSUMÉ DE LA SYNCHRONISATION:\n"
        summary += "-" * 40 + "\n"

        total_imported = 0
        total_errors = 0

        for sync_type, result in sync_results.items():
            status_icon = "✅" if result.get('success', False) else "❌"
            imported = result.get('imported_count', 0) or result.get('total_imported', 0)
            errors = result.get('error_count', 0) or result.get('total_errors', 0)

            total_imported += imported
            total_errors += errors

            summary += f"{status_icon} {sync_type.upper()}: {imported} importés, {errors} erreurs\n"

        summary += "-" * 40 + "\n"
        summary += f"🔢 TOTAL: {total_imported} éléments importés, {total_errors} erreurs\n"
        summary += f"⏱️  Durée: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        return summary

    def get_sync_status(self, job_id: int) -> Dict[str, Any]:
        """
        Récupère le statut d'un job de synchronisation

        Args:
            job_id: ID du job de synchronisation

        Returns:
            Statut du job
        """
        try:
            job = SyncJob.objects.get(id=job_id)
            return {
                'id': job.id,
                'status': job.status,
                'progress': job.progress,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'log_message': job.log_message,
                'processed_items': job.processed_items,
                'success_count': job.success_count,
                'error_count': job.error_count
            }
        except SyncJob.DoesNotExist:
            return {'error': 'Job de synchronisation introuvable'}