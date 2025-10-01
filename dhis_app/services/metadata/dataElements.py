"""
Service de synchronisation des elements de donnees DHIS2
Respecte l'ordre d'importation DHIS2: dataElements -> dataElementGroups -> dataElementGroupSets
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class DataElementsService(BaseMetadataService):
    """Service de synchronisation des elements de donnees"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les elements de donnees"""
        try:
            if job:
                job.log_message += "Synchronisation de dataElements...\n"
                job.save()

            data_elements = self.source_instance.get_metadata(
                resource='dataElements',
                fields='id,name,code,displayName,shortName,description,valueType,aggregationType,domainType,categoryCombo[id],optionSet[id],zeroIsSignificant,sharing',
                paging=True,
                page_size=100
            )


            source_count = len(data_elements)

            if not data_elements:
                if job:
                    job.log_message += self._format_sync_log('dataElements', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            data_elements = self.clean_sharing_user_references(data_elements, 'dataElements')

            result = self.destination_instance.post_metadata(
                resource='dataElements',
                data=data_elements,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('dataElements', source_count, stats)
                job.save()

            return {
                'success': True,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer dataElements: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR dataElements: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class DataElementGroupsService(BaseMetadataService):
    """Service de synchronisation des groupes d'elements de donnees"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les groupes d'elements de donnees"""
        try:
            if job:
                job.log_message += "Synchronisation de dataElementGroups...\n"
                job.save()

            groups = self.source_instance.get_metadata(
                resource='dataElementGroups',
                fields='id,name,code,displayName,shortName,description,dataElements[id],sharing',
                paging=False
            )


            source_count = len(groups)

            if not groups:
                if job:
                    job.log_message += self._format_sync_log('dataElementGroups', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            groups = self.clean_sharing_user_references(groups, 'dataElementGroups')

            result = self.destination_instance.post_metadata(
                resource='dataElementGroups',
                data=groups,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('dataElementGroups', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer dataElementGroups: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR dataElementGroups: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class DataElementGroupSetsService(BaseMetadataService):
    """Service de synchronisation des ensembles de groupes d'elements de donnees"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les ensembles de groupes d'elements de donnees"""
        try:
            if job:
                job.log_message += "Synchronisation de dataElementGroupSets...\n"
                job.save()

            group_sets = self.source_instance.get_metadata(
                resource='dataElementGroupSets',
                fields='id,name,shortName,code,displayName,description,compulsory,dataDimension,dataElementGroups[id],sharing',
                paging=False
            )


            source_count = len(group_sets)

            if not group_sets:
                if job:
                    job.log_message += self._format_sync_log('dataElementGroupSets', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            group_sets = self.clean_sharing_user_references(group_sets, 'dataElementGroupSets')

            result = self.destination_instance.post_metadata(
                resource='dataElementGroupSets',
                data=group_sets,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('dataElementGroupSets', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer dataElementGroupSets: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR dataElementGroupSets: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class DataElementsSyncService:
    """
    Service orchestrateur pour la synchronisation des elements de donnees
    Respecte l'ordre DHIS2: dataElements -> dataElementGroups -> dataElementGroupSets
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.elements_service = DataElementsService(sync_config)
        self.groups_service = DataElementGroupsService(sync_config)
        self.group_sets_service = DataElementGroupSetsService(sync_config)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux elements de donnees dans l'ordre correct

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

            # 1. dataElements (obligatoire en premier)
            elements_result = self.elements_service.sync(job, strategy)
            results['dataElements'] = elements_result
            total_imported += elements_result.get('imported_count', 0)
            if not elements_result.get('success', False):
                total_errors += 1

            # 2. dataElementGroups (necessite dataElements)
            groups_result = self.groups_service.sync(job, strategy)
            results['dataElementGroups'] = groups_result
            total_imported += groups_result.get('imported_count', 0)
            if not groups_result.get('success', False):
                total_errors += 1

            # 3. dataElementGroupSets (necessite dataElementGroups)
            group_sets_result = self.group_sets_service.sync(job, strategy)
            results['dataElementGroupSets'] = group_sets_result
            total_imported += group_sets_result.get('imported_count', 0)
            if not group_sets_result.get('success', False):
                total_errors += 1

            return {
                'success': total_errors == 0,
                'results': results,
                'total_imported': total_imported,
                'total_errors': total_errors
            }

        except Exception as e:
            error_msg = f"Erreur lors de la synchronisation des elements de donnees: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}