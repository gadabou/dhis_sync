"""
Service de synchronisation des predicteurs DHIS2
Respecte l'ordre d'importation DHIS2: predictors -> predictorGroups
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class PredictorsService(BaseMetadataService):
    """Service de synchronisation des predicteurs"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les predicteurs"""
        try:
            if job:
                job.log_message += "Synchronisation de predictors...\n"
                job.save()

            predictors = self.source_instance.get_metadata(
                resource='predictors',
                fields='id,name,shortName,displayName,code,description,output[id],periodType,sequentialSampleCount,sequentialSkipCount,annualSampleCount,generator[expression,description,missingValueStrategy],organisationUnitLevels,organisationUnitDescendants,sharing',
                paging=False
            )


            source_count = len(predictors)

            if not predictors:
                if job:
                    job.log_message += self._format_sync_log('predictors', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            predictors = self.clean_sharing_user_references(predictors, 'predictors')

            result = self.destination_instance.post_metadata(
                resource='predictors',
                data=predictors,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('predictors', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer predictors: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR predictors: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class PredictorGroupsService(BaseMetadataService):
    """Service de synchronisation des groupes de predicteurs"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les groupes de predicteurs"""
        try:
            if job:
                job.log_message += "Synchronisation de predictorGroups...\n"
                job.save()

            groups = self.source_instance.get_metadata(
                resource='predictorGroups',
                fields='id,name,displayName,code,description,predictors[id],sharing',
                paging=False
            )


            source_count = len(groups)

            if not groups:
                if job:
                    job.log_message += self._format_sync_log('predictorGroups', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            groups = self.clean_sharing_user_references(groups, 'predictorGroups')

            result = self.destination_instance.post_metadata(
                resource='predictorGroups',
                data=groups,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('predictorGroups', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer predictorGroups: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR predictorGroups: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class PredictorsSyncService:
    """
    Service orchestrateur pour la synchronisation des predicteurs
    Respecte l'ordre DHIS2: predictors -> predictorGroups
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.predictors_service = PredictorsService(sync_config)
        self.groups_service = PredictorGroupsService(sync_config)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux predicteurs dans l'ordre correct

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

            # 1. predictors (obligatoire en premier)
            predictors_result = self.predictors_service.sync(job, strategy)
            results['predictors'] = predictors_result
            total_imported += predictors_result.get('imported_count', 0)
            if not predictors_result.get('success', False):
                total_errors += 1

            # 2. predictorGroups (necessite predictors)
            groups_result = self.groups_service.sync(job, strategy)
            results['predictorGroups'] = groups_result
            total_imported += groups_result.get('imported_count', 0)
            if not groups_result.get('success', False):
                total_errors += 1

            return {
                'success': total_errors == 0,
                'results': results,
                'total_imported': total_imported,
                'total_errors': total_errors
            }

        except Exception as e:
            error_msg = f"Erreur lors de la synchronisation des predicteurs: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}