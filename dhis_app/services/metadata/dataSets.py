"""
Service de synchronisation des ensembles de donnees DHIS2
Respecte l'ordre d'importation DHIS2: dataSets -> sections -> dataSetElements
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class DataSetsService(BaseMetadataService):
    """Service de synchronisation des ensembles de donnees"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les ensembles de donnees"""
        try:
            if job:
                job.log_message += "Synchronisation de dataSets...\n"
                job.save()

            data_sets = self.source_instance.get_metadata(
                resource='dataSets',
                fields='id,name,code,displayName,shortName,description,periodType,categoryCombo[id],mobile,version,expiryDays,timelyDays,notifyCompletingUser,openFuturePeriods,openPeriodsAfterCoEndDate,fieldCombinationRequired,validCompleteOnly,noValueRequiresComment,skipOffline,dataElementDecoration,renderAsTabs,renderHorizontally,compulsoryFieldsCompleteOnly,formType,dataSetElements[dataElement[id],categoryCombo[id]],indicators[id],organisationUnits[id],sections[id]',
                paging=False
            )

            if not data_sets:
                if job:
                    job.log_message += "Resultat dataSets: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='dataSets',
                data=data_sets,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat dataSets: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': True,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer dataSets: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR dataSets: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class SectionsService(BaseMetadataService):
    """Service de synchronisation des sections"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les sections"""
        try:
            if job:
                job.log_message += "Synchronisation de sections...\n"
                job.save()

            sections = self.source_instance.get_metadata(
                resource='sections',
                fields='id,name,displayName,description,sortOrder,dataSet[id],dataElements[id],indicators[id],categoryCombos[id],greyedFields[dataElement[id],categoryOptionCombo[id]]',
                paging=False
            )

            if not sections:
                if job:
                    job.log_message += "Resultat sections: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='sections',
                data=sections,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat sections: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer sections: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR sections: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class DataSetsSyncService:
    """
    Service orchestrateur pour la synchronisation des ensembles de donnees
    Respecte l'ordre DHIS2: dataSets -> sections
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.data_sets_service = DataSetsService(self.source, self.dest)
        self.sections_service = SectionsService(self.source, self.dest)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux ensembles de donnees dans l'ordre correct

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

            # 1. dataSets (obligatoire en premier)
            data_sets_result = self.data_sets_service.sync(job, strategy)
            results['dataSets'] = data_sets_result
            total_imported += data_sets_result.get('imported_count', 0)
            if not data_sets_result.get('success', False):
                total_errors += 1

            # 2. sections (necessite dataSets)
            sections_result = self.sections_service.sync(job, strategy)
            results['sections'] = sections_result
            total_imported += sections_result.get('imported_count', 0)
            if not sections_result.get('success', False):
                total_errors += 1

            return {
                'success': total_errors == 0,
                'results': results,
                'total_imported': total_imported,
                'total_errors': total_errors
            }

        except Exception as e:
            error_msg = f"Erreur lors de la synchronisation des ensembles de donnees: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}