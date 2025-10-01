"""
Service de synchronisation des categories DHIS2
Respecte l'ordre d'importation DHIS2: categoryOptions -> categories -> categoryCombos -> categoryOptionGroups -> categoryOptionGroupSets
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class CategoryOptionsService(BaseMetadataService):
    """Service de synchronisation des options de categories"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les options de categories"""
        try:
            if job:
                job.log_message += "Synchronisation de categoryOptions...\n"
                job.save()

            options = self.source_instance.get_metadata(
                resource='categoryOptions',
                fields='id,name,code,displayName,shortName,description,startDate,endDate,organisationUnits[id],sharing',
                paging=False
            )


            source_count = len(options)

            if not options:
                if job:
                    job.log_message += self._format_sync_log('categoryOptions', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='categoryOptions',
                data=options,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('categoryOptions', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer categoryOptions: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR categoryOptions: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class CategoriesService(BaseMetadataService):
    """Service de synchronisation des categories"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les categories"""
        try:
            if job:
                job.log_message += "Synchronisation de categories...\n"
                job.save()

            categories = self.source_instance.get_metadata(
                resource='categories',
                fields='id,name,code,displayName,shortName,description,dataDimensionType,categoryOptions[id],sharing',
                paging=False
            )


            source_count = len(categories)

            if not categories:
                if job:
                    job.log_message += self._format_sync_log('categories', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='categories',
                data=categories,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('categories', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer categories: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR categories: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class CategoryCombosService(BaseMetadataService):
    """Service de synchronisation des combinaisons de categories"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les combinaisons de categories"""
        try:
            if job:
                job.log_message += "Synchronisation de categoryCombos...\n"
                job.save()

            combos = self.source_instance.get_metadata(
                resource='categoryCombos',
                fields='id,name,code,displayName,dataDimensionType,skipTotal,categories[id],sharing',
                paging=False
            )


            source_count = len(combos)

            if not combos:
                if job:
                    job.log_message += self._format_sync_log('categoryCombos', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='categoryCombos',
                data=combos,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('categoryCombos', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer categoryCombos: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR categoryCombos: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class CategoryOptionCombosService(BaseMetadataService):
    """Service de synchronisation des combinaisons d'options de categories"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les combinaisons d'options de categories"""
        try:
            if job:
                job.log_message += "Synchronisation de categoryOptionCombos...\n"
                job.save()

            option_combos = self.source_instance.get_metadata(
                resource='categoryOptionCombos',
                fields='id,name,shortName,code,displayName,categoryCombo[id],categoryOptions[id],sharing',
                paging=True,
                page_size=100
            )


            source_count = len(option_combos)

            if not option_combos:
                if job:
                    job.log_message += self._format_sync_log('categoryOptionCombos', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='categoryOptionCombos',
                data=option_combos,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('categoryOptionCombos', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer categoryOptionCombos: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR categoryOptionCombos: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class CategoryOptionGroupsService(BaseMetadataService):
    """Service de synchronisation des groupes d'options de categories"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les groupes d'options de categories"""
        try:
            if job:
                job.log_message += "Synchronisation de categoryOptionGroups...\n"
                job.save()

            groups = self.source_instance.get_metadata(
                resource='categoryOptionGroups',
                fields='id,name,code,displayName,shortName,categoryOptions[id],sharing',
                paging=False
            )


            source_count = len(groups)

            if not groups:
                if job:
                    job.log_message += self._format_sync_log('categoryOptionGroups', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='categoryOptionGroups',
                data=groups,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('categoryOptionGroups', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer categoryOptionGroups: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR categoryOptionGroups: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class CategoryOptionGroupSetsService(BaseMetadataService):
    """Service de synchronisation des ensembles de groupes d'options de categories"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les ensembles de groupes d'options de categories"""
        try:
            if job:
                job.log_message += "Synchronisation de categoryOptionGroupSets...\n"
                job.save()

            group_sets = self.source_instance.get_metadata(
                resource='categoryOptionGroupSets',
                fields='id,name,shortName,code,displayName,description,dataDimension,categoryOptionGroups[id],sharing',
                paging=False
            )


            source_count = len(group_sets)

            if not group_sets:
                if job:
                    job.log_message += self._format_sync_log('categoryOptionGroupSets', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='categoryOptionGroupSets',
                data=group_sets,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('categoryOptionGroupSets', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer categoryOptionGroupSets: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR categoryOptionGroupSets: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class CategoriesSyncService:
    """
    Service orchestrateur pour la synchronisation des categories
    Respecte l'ordre DHIS2: categoryOptions -> categories -> categoryCombos -> categoryOptionCombos -> categoryOptionGroups -> categoryOptionGroupSets
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.options_service = CategoryOptionsService(sync_config)
        self.categories_service = CategoriesService(sync_config)
        self.combos_service = CategoryCombosService(sync_config)
        self.option_combos_service = CategoryOptionCombosService(sync_config)
        self.option_groups_service = CategoryOptionGroupsService(sync_config)
        self.option_group_sets_service = CategoryOptionGroupSetsService(sync_config)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux categories dans l'ordre correct

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

            # 1. categoryOptions (obligatoire en premier)
            options_result = self.options_service.sync(job, strategy)
            results['categoryOptions'] = options_result
            total_imported += options_result.get('imported_count', 0)
            if not options_result.get('success', False):
                total_errors += 1

            # 2. categories (necessite categoryOptions)
            categories_result = self.categories_service.sync(job, strategy)
            results['categories'] = categories_result
            total_imported += categories_result.get('imported_count', 0)
            if not categories_result.get('success', False):
                total_errors += 1

            # 3. categoryCombos (necessite categories)
            combos_result = self.combos_service.sync(job, strategy)
            results['categoryCombos'] = combos_result
            total_imported += combos_result.get('imported_count', 0)
            if not combos_result.get('success', False):
                total_errors += 1

            # 4. categoryOptionCombos (necessite categoryCombos et categoryOptions)
            option_combos_result = self.option_combos_service.sync(job, strategy)
            results['categoryOptionCombos'] = option_combos_result
            total_imported += option_combos_result.get('imported_count', 0)
            if not option_combos_result.get('success', False):
                total_errors += 1

            # 5. categoryOptionGroups (necessite categoryOptions)
            groups_result = self.option_groups_service.sync(job, strategy)
            results['categoryOptionGroups'] = groups_result
            total_imported += groups_result.get('imported_count', 0)
            if not groups_result.get('success', False):
                total_errors += 1

            # 6. categoryOptionGroupSets (necessite categoryOptionGroups)
            group_sets_result = self.option_group_sets_service.sync(job, strategy)
            results['categoryOptionGroupSets'] = group_sets_result
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
            error_msg = f"Erreur lors de la synchronisation des categories: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}