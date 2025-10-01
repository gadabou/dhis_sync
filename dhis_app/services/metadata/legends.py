"""
Service de synchronisation des legendes DHIS2
Respecte l'ordre d'importation DHIS2: legends -> legendSets
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class LegendsService(BaseMetadataService):
    """Service de synchronisation des legendes"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les legendes"""
        try:
            if job:
                job.log_message += "Synchronisation de legends...\n"
                job.save()

            legends = self.source_instance.get_metadata(
                resource='legends',
                fields='id,name,displayName,startValue,endValue,color,sharing',
                paging=False
            )


            source_count = len(legends)

            if not legends:
                if job:
                    job.log_message += self._format_sync_log('legends', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            legends = self.clean_sharing_user_references(legends, 'legends')

            result = self.destination_instance.post_metadata(
                resource='legends',
                data=legends,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('legends', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_str = str(e)
            # Gérer gracieusement les ressources non disponibles (404)
            if "404" in error_str or "Not Found" in error_str:
                self.logger.warning(f"Ressource legends non disponible sur l'instance source (404) - ignorée")
                if job:
                    job.log_message += "INFO: Ressource legends non disponible (404) - ignorée\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            error_msg = f"Impossible d'importer legends: {error_str}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR legends: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class LegendSetsService(BaseMetadataService):
    """Service de synchronisation des ensembles de legendes"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les ensembles de legendes"""
        try:
            if job:
                job.log_message += "Synchronisation de legendSets...\n"
                job.save()

            legend_sets = self.source_instance.get_metadata(
                resource='legendSets',
                fields='id,name,displayName,code,description,symbolizer,legends[id],sharing',
                paging=False
            )


            source_count = len(legend_sets)

            if not legend_sets:
                if job:
                    job.log_message += self._format_sync_log('legendSets', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            legend_sets = self.clean_sharing_user_references(legend_sets, 'legendSets')

            result = self.destination_instance.post_metadata(
                resource='legendSets',
                data=legend_sets,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('legendSets', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_str = str(e)
            # Gérer gracieusement les ressources non disponibles (404)
            if "404" in error_str or "Not Found" in error_str:
                self.logger.warning(f"Ressource legendSets non disponible sur l'instance source (404) - ignorée")
                if job:
                    job.log_message += "INFO: Ressource legendSets non disponible (404) - ignorée\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            error_msg = f"Impossible d'importer legendSets: {error_str}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR legendSets: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class LegendsSyncService:
    """
    Service orchestrateur pour la synchronisation des legendes
    Respecte l'ordre DHIS2: legends -> legendSets
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.legends_service = LegendsService(sync_config)
        self.legend_sets_service = LegendSetsService(sync_config)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux legendes dans l'ordre correct

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            strategy = self.sync_config.import_strategy
            results = {}
            total_imported = 0
            total_errors = 0

            # 1. legends (obligatoire en premier)
            legends_result = self.legends_service.sync(job, strategy)
            results['legends'] = legends_result
            total_imported += legends_result.get('imported_count', 0)
            if not legends_result.get('success', False):
                total_errors += 1

            # 2. legendSets (necessite legends)
            legend_sets_result = self.legend_sets_service.sync(job, strategy)
            results['legendSets'] = legend_sets_result
            total_imported += legend_sets_result.get('imported_count', 0)
            if not legend_sets_result.get('success', False):
                total_errors += 1

            return {
                'success': total_errors == 0,
                'results': results,
                'total_imported': total_imported,
                'total_errors': total_errors
            }

        except Exception as e:
            error_msg = f"Erreur lors de la synchronisation des legendes: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}