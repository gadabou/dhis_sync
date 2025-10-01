"""
Service de synchronisation des unites d'organisation DHIS2
Respecte l'ordre d'importation DHIS2: organisationUnitLevels -> organisationUnits -> organisationUnitGroups -> organisationUnitGroupSets
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class OrganisationUnitLevelsService(BaseMetadataService):
    """Service de synchronisation des niveaux d'unites d'organisation"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les niveaux d'unites d'organisation"""
        try:
            if job:
                job.log_message += "Synchronisation de organisationUnitLevels...\n"
                job.save()

            levels = self.source_instance.get_metadata(
                resource='organisationUnitLevels',
                fields='id,name,displayName,level,offlineLevels',
                paging=False
            )


            source_count = len(levels)

            if not levels:
                if job:
                    job.log_message += self._format_sync_log('organisationUnitLevels', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='organisationUnitLevels',
                data=levels,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('organisationUnitLevels', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer organisationUnitLevels: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR organisationUnitLevels: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class OrganisationUnitsService(BaseMetadataService):
    """Service de synchronisation des unites d'organisation"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les unites d'organisation"""
        try:
            if job:
                job.log_message += "Synchronisation de organisationUnits...\n"
                job.save()

            # Recuperer les unites d'organisation
            org_units = self.source_instance.get_metadata(
                resource='organisationUnits',
                fields='id,name,code,displayName,shortName,description,openingDate,closedDate,parent[id],level,path,geometry,attributeValues',
                paging=True,
                page_size=100
            )

            source_count = len(org_units)

            if not org_units:
                if job:
                    job.log_message += self._format_sync_log('organisationUnits', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Trier par niveau pour respecter la hierarchie (parents avant enfants)
            org_units_sorted = sorted(org_units, key=lambda x: x.get('level', 0))

            if job:
                job.log_message += f"  {len(org_units_sorted)} unites trouvees, triees par niveau hierarchique\n"
                job.save()

            # Importer les unites d'organisation
            result = self.destination_instance.post_metadata(
                resource='organisationUnits',
                data=org_units_sorted,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('organisationUnits', source_count, stats)
                job.save()

            return {
                'success': True,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer organisationUnits: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR organisationUnits: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class OrganisationUnitGroupsService(BaseMetadataService):
    """Service de synchronisation des groupes d'unites d'organisation"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les groupes d'unites d'organisation"""
        try:
            if job:
                job.log_message += "Synchronisation de organisationUnitGroups...\n"
                job.save()

            groups = self.source_instance.get_metadata(
                resource='organisationUnitGroups',
                fields='id,name,code,displayName,shortName,description,organisationUnits[id],attributeValues,sharing',
                paging=False
            )


            source_count = len(groups)

            if not groups:
                if job:
                    job.log_message += self._format_sync_log('organisationUnitGroups', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='organisationUnitGroups',
                data=groups,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('organisationUnitGroups', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer organisationUnitGroups: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR organisationUnitGroups: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class OrganisationUnitGroupSetsService(BaseMetadataService):
    """Service de synchronisation des ensembles de groupes d'unites d'organisation"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les ensembles de groupes d'unites d'organisation"""
        try:
            if job:
                job.log_message += "Synchronisation de organisationUnitGroupSets...\n"
                job.save()

            group_sets = self.source_instance.get_metadata(
                resource='organisationUnitGroupSets',
                fields='id,name,shortName,code,displayName,description,compulsory,includeSubhierarchyInAnalytics,organisationUnitGroups[id],attributeValues,sharing',
                paging=False
            )


            source_count = len(group_sets)

            if not group_sets:
                if job:
                    job.log_message += self._format_sync_log('organisationUnitGroupSets', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='organisationUnitGroupSets',
                data=group_sets,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('organisationUnitGroupSets', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer organisationUnitGroupSets: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR organisationUnitGroupSets: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class OrganisationUnitsSyncService:
    """
    Service orchestrateur pour la synchronisation des unites d'organisation
    Respecte l'ordre DHIS2: organisationUnitLevels -> organisationUnits -> organisationUnitGroups -> organisationUnitGroupSets
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.levels_service = OrganisationUnitLevelsService(sync_config)
        self.units_service = OrganisationUnitsService(sync_config)
        self.groups_service = OrganisationUnitGroupsService(sync_config)
        self.group_sets_service = OrganisationUnitGroupSetsService(sync_config)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux unites d'organisation dans l'ordre correct

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

            # 1. organisationUnitLevels (obligatoire en premier)
            levels_result = self.levels_service.sync(job, strategy)
            results['organisationUnitLevels'] = levels_result
            total_imported += levels_result.get('imported_count', 0)
            if not levels_result.get('success', False):
                total_errors += 1

            # 2. organisationUnits (necessite organisationUnitLevels)
            units_result = self.units_service.sync(job, strategy)
            results['organisationUnits'] = units_result
            total_imported += units_result.get('imported_count', 0)
            if not units_result.get('success', False):
                total_errors += 1

            # 3. organisationUnitGroups (necessite organisationUnits)
            groups_result = self.groups_service.sync(job, strategy)
            results['organisationUnitGroups'] = groups_result
            total_imported += groups_result.get('imported_count', 0)
            if not groups_result.get('success', False):
                total_errors += 1

            # 4. organisationUnitGroupSets (necessite organisationUnitGroups)
            group_sets_result = self.group_sets_service.sync(job, strategy)
            results['organisationUnitGroupSets'] = group_sets_result
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
            error_msg = f"Erreur lors de la synchronisation des unites d'organisation: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}