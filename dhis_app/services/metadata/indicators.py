"""
Service de synchronisation des indicateurs DHIS2
Respecte l'ordre d'importation DHIS2: indicatorTypes -> indicators -> indicatorGroups -> indicatorGroupSets
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class IndicatorTypesService(BaseMetadataService):
    """Service de synchronisation des types d'indicateurs"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les types d'indicateurs"""
        try:
            if job:
                job.log_message += "Synchronisation de indicatorTypes...\n"
                job.save()

            indicator_types = self.source_instance.get_metadata(
                resource='indicatorTypes',
                fields='id,name,shortName,displayName,factor,number,sharing',
                paging=False
            )


            source_count = len(indicator_types)

            if not indicator_types:
                if job:
                    job.log_message += self._format_sync_log('indicatorTypes', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            indicator_types = self.clean_sharing_user_references(indicator_types, 'indicatorTypes')

            result = self.destination_instance.post_metadata(
                resource='indicatorTypes',
                data=indicator_types,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('indicatorTypes', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer indicatorTypes: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR indicatorTypes: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class IndicatorsService(BaseMetadataService):
    """Service de synchronisation des indicateurs"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les indicateurs"""
        try:
            if job:
                job.log_message += "Synchronisation de indicators...\n"
                job.save()

            indicators = self.source_instance.get_metadata(
                resource='indicators',
                fields='id,name,code,displayName,shortName,description,annualized,decimals,indicatorType[id],numerator,numeratorDescription,denominator,denominatorDescription,sharing',
                paging=True,
                page_size=100
            )


            source_count = len(indicators)

            if not indicators:
                if job:
                    job.log_message += self._format_sync_log('indicators', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            indicators = self.clean_sharing_user_references(indicators, 'indicators')

            result = self.destination_instance.post_metadata(
                resource='indicators',
                data=indicators,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('indicators', source_count, stats)
                job.save()

            return {
                'success': True,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer indicators: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR indicators: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class IndicatorGroupsService(BaseMetadataService):
    """Service de synchronisation des groupes d'indicateurs"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les groupes d'indicateurs"""
        try:
            if job:
                job.log_message += "Synchronisation de indicatorGroups...\n"
                job.save()

            groups = self.source_instance.get_metadata(
                resource='indicatorGroups',
                fields='id,name,code,displayName,description,indicators[id],sharing',
                paging=False
            )


            source_count = len(groups)

            if not groups:
                if job:
                    job.log_message += self._format_sync_log('indicatorGroups', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            groups = self.clean_sharing_user_references(groups, 'indicatorGroups')

            result = self.destination_instance.post_metadata(
                resource='indicatorGroups',
                data=groups,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('indicatorGroups', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer indicatorGroups: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR indicatorGroups: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class IndicatorGroupSetsService(BaseMetadataService):
    """Service de synchronisation des ensembles de groupes d'indicateurs"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les ensembles de groupes d'indicateurs"""
        try:
            if job:
                job.log_message += "Synchronisation de indicatorGroupSets...\n"
                job.save()

            group_sets = self.source_instance.get_metadata(
                resource='indicatorGroupSets',
                fields='id,name,shortName,code,displayName,description,compulsory,indicatorGroups[id],sharing',
                paging=False
            )


            source_count = len(group_sets)

            if not group_sets:
                if job:
                    job.log_message += self._format_sync_log('indicatorGroupSets', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            group_sets = self.clean_sharing_user_references(group_sets, 'indicatorGroupSets')

            result = self.destination_instance.post_metadata(
                resource='indicatorGroupSets',
                data=group_sets,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('indicatorGroupSets', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer indicatorGroupSets: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR indicatorGroupSets: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class IndicatorsSyncService:
    """
    Service orchestrateur pour la synchronisation des indicateurs
    Respecte l'ordre DHIS2: indicatorTypes -> indicators -> indicatorGroups -> indicatorGroupSets
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.types_service = IndicatorTypesService(sync_config)
        self.indicators_service = IndicatorsService(sync_config)
        self.groups_service = IndicatorGroupsService(sync_config)
        self.group_sets_service = IndicatorGroupSetsService(sync_config)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux indicateurs dans l'ordre correct

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

            # 1. indicatorTypes (obligatoire en premier)
            types_result = self.types_service.sync(job, strategy)
            results['indicatorTypes'] = types_result
            total_imported += types_result.get('imported_count', 0)
            if not types_result.get('success', False):
                total_errors += 1

            # 2. indicators (necessite indicatorTypes)
            indicators_result = self.indicators_service.sync(job, strategy)
            results['indicators'] = indicators_result
            total_imported += indicators_result.get('imported_count', 0)
            if not indicators_result.get('success', False):
                total_errors += 1

            # 3. indicatorGroups (necessite indicators)
            groups_result = self.groups_service.sync(job, strategy)
            results['indicatorGroups'] = groups_result
            total_imported += groups_result.get('imported_count', 0)
            if not groups_result.get('success', False):
                total_errors += 1

            # 4. indicatorGroupSets (necessite indicatorGroups)
            group_sets_result = self.group_sets_service.sync(job, strategy)
            results['indicatorGroupSets'] = group_sets_result
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
            error_msg = f"Erreur lors de la synchronisation des indicateurs: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}