"""
Service de synchronisation des entites suivies DHIS2
Respecte l'ordre d'importation DHIS2: trackedEntityTypes -> trackedEntityAttributes -> trackedEntityAttributeGroups
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class TrackedEntityTypesService(BaseMetadataService):
    """Service de synchronisation des types d'entites suivies"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les types d'entites suivies"""
        try:
            if job:
                job.log_message += "Synchronisation de trackedEntityTypes...\n"
                job.save()

            entity_types = self.source_instance.get_metadata(
                resource='trackedEntityTypes',
                fields='id,name,shortName,displayName,description,code,sharing',
                paging=False
            )


            source_count = len(entity_types)

            if not entity_types:
                if job:
                    job.log_message += self._format_sync_log('trackedEntityTypes', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            entity_types = self.clean_sharing_user_references(entity_types, 'trackedEntityTypes')

            result = self.destination_instance.post_metadata(
                resource='trackedEntityTypes',
                data=entity_types,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('trackedEntityTypes', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer trackedEntityTypes: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR trackedEntityTypes: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class TrackedEntityAttributesService(BaseMetadataService):
    """Service de synchronisation des attributs d'entites suivies"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les attributs d'entites suivies"""
        try:
            if job:
                job.log_message += "Synchronisation de trackedEntityAttributes...\n"
                job.save()

            attributes = self.source_instance.get_metadata(
                resource='trackedEntityAttributes',
                fields='id,name,shortName,displayName,code,description,valueType,aggregationType,unique,inherit,optionSet[id],generated,pattern,orgunitScope,confidential,sharing',
                paging=False
            )


            source_count = len(attributes)

            if not attributes:
                if job:
                    job.log_message += self._format_sync_log('trackedEntityAttributes', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            attributes = self.clean_sharing_user_references(attributes, 'trackedEntityAttributes')

            result = self.destination_instance.post_metadata(
                resource='trackedEntityAttributes',
                data=attributes,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('trackedEntityAttributes', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer trackedEntityAttributes: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR trackedEntityAttributes: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class TrackerSyncService:
    """
    Service orchestrateur pour la synchronisation des entites suivies
    Respecte l'ordre DHIS2: trackedEntityTypes -> trackedEntityAttributes
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.entity_types_service = TrackedEntityTypesService(sync_config)
        self.attributes_service = TrackedEntityAttributesService(sync_config)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux entites suivies dans l'ordre correct

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

            # 1. trackedEntityTypes (obligatoire en premier)
            types_result = self.entity_types_service.sync(job, strategy)
            results['trackedEntityTypes'] = types_result
            total_imported += types_result.get('imported_count', 0)
            if not types_result.get('success', False):
                total_errors += 1

            # 2. trackedEntityAttributes
            attributes_result = self.attributes_service.sync(job, strategy)
            results['trackedEntityAttributes'] = attributes_result
            total_imported += attributes_result.get('imported_count', 0)
            if not attributes_result.get('success', False):
                total_errors += 1

            return {
                'success': total_errors == 0,
                'results': results,
                'total_imported': total_imported,
                'total_errors': total_errors
            }

        except Exception as e:
            error_msg = f"Erreur lors de la synchronisation des entites suivies: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}