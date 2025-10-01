"""
Service de synchronisation des options DHIS2
Respecte l'ordre d'importation DHIS2: options -> optionSets -> optionGroups -> optionGroupSets
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class OptionsService(BaseMetadataService):
    """Service de synchronisation des options"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les options"""
        try:
            if job:
                job.log_message += "Synchronisation de options...\n"
                job.save()

            options = self.source_instance.get_metadata(
                resource='options',
                fields='id,name,shortName,code,displayName,sortOrder,optionSet[id],sharing',
                paging=True,
                page_size=100
            )


            source_count = len(options)

            if not options:
                if job:
                    job.log_message += self._format_sync_log('options', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            options = self.clean_sharing_user_references(options, 'options')

            result = self.destination_instance.post_metadata(
                resource='options',
                data=options,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('options', source_count, stats)
                job.save()

            return {
                'success': True,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer options: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR options: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class OptionSetsService(BaseMetadataService):
    """Service de synchronisation des ensembles d'options"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les ensembles d'options"""
        try:
            if job:
                job.log_message += "Synchronisation de optionSets...\n"
                job.save()

            option_sets = self.source_instance.get_metadata(
                resource='optionSets',
                fields='id,name,shortName,code,displayName,valueType,options[id],sharing',
                paging=False
            )


            source_count = len(option_sets)

            if not option_sets:
                if job:
                    job.log_message += self._format_sync_log('optionSets', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            option_sets = self.clean_sharing_user_references(option_sets, 'optionSets')

            result = self.destination_instance.post_metadata(
                resource='optionSets',
                data=option_sets,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('optionSets', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer optionSets: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR optionSets: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class OptionGroupsService(BaseMetadataService):
    """Service de synchronisation des groupes d'options"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les groupes d'options"""
        try:
            if job:
                job.log_message += "Synchronisation de optionGroups...\n"
                job.save()

            groups = self.source_instance.get_metadata(
                resource='optionGroups',
                fields='id,name,code,displayName,shortName,options[id],optionSet[id],sharing',
                paging=False
            )


            source_count = len(groups)

            if not groups:
                if job:
                    job.log_message += self._format_sync_log('optionGroups', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            groups = self.clean_sharing_user_references(groups, 'optionGroups')

            result = self.destination_instance.post_metadata(
                resource='optionGroups',
                data=groups,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('optionGroups', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer optionGroups: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR optionGroups: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class OptionGroupSetsService(BaseMetadataService):
    """Service de synchronisation des ensembles de groupes d'options"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les ensembles de groupes d'options"""
        try:
            if job:
                job.log_message += "Synchronisation de optionGroupSets...\n"
                job.save()

            group_sets = self.source_instance.get_metadata(
                resource='optionGroupSets',
                fields='id,name,code,displayName,description,dataDimension,optionGroups[id],sharing',
                paging=False
            )


            source_count = len(group_sets)

            if not group_sets:
                if job:
                    job.log_message += self._format_sync_log('optionGroupSets', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            group_sets = self.clean_sharing_user_references(group_sets, 'optionGroupSets')

            result = self.destination_instance.post_metadata(
                resource='optionGroupSets',
                data=group_sets,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('optionGroupSets', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer optionGroupSets: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR optionGroupSets: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class OptionsSyncService:
    """
    Service orchestrateur pour la synchronisation des options
    Respecte l'ordre DHIS2: options -> optionSets -> optionGroups -> optionGroupSets
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.options_service = OptionsService(sync_config)
        self.option_sets_service = OptionSetsService(sync_config)
        self.option_groups_service = OptionGroupsService(sync_config)
        self.option_group_sets_service = OptionGroupSetsService(sync_config)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux options dans l'ordre correct

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

            # 1. options (obligatoire en premier)
            options_result = self.options_service.sync(job, strategy)
            results['options'] = options_result
            total_imported += options_result.get('imported_count', 0)
            if not options_result.get('success', False):
                total_errors += 1

            # 2. optionSets (necessite options)
            option_sets_result = self.option_sets_service.sync(job, strategy)
            results['optionSets'] = option_sets_result
            total_imported += option_sets_result.get('imported_count', 0)
            if not option_sets_result.get('success', False):
                total_errors += 1

            # 3. optionGroups (necessite options et optionSets)
            groups_result = self.option_groups_service.sync(job, strategy)
            results['optionGroups'] = groups_result
            total_imported += groups_result.get('imported_count', 0)
            if not groups_result.get('success', False):
                total_errors += 1

            # 4. optionGroupSets (necessite optionGroups)
            group_sets_result = self.option_group_sets_service.sync(job, strategy)
            results['optionGroupSets'] = group_sets_result
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
            error_msg = f"Erreur lors de la synchronisation des options: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}