"""
Service de synchronisation des attributs et constantes DHIS2
Respecte l'ordre d'importation DHIS2: attributes -> constants
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class AttributesService(BaseMetadataService):
    """Service de synchronisation des attributs"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les attributs"""
        try:
            if job:
                job.log_message += "Synchronisation de attributes...\n"
                job.save()

            attributes = self.source_instance.get_metadata(
                resource='attributes',
                fields='id,name,displayName,code,valueType,mandatory,unique,dataElementAttribute,indicatorAttribute,organisationUnitAttribute,userAttribute,categoryOptionAttribute,optionSetAttribute,programAttribute,programStageAttribute,trackedEntityAttributeAttribute,dataSetAttribute,documentAttribute,optionSet[id]',
                paging=False
            )

            if not attributes:
                if job:
                    job.log_message += "Resultat attributes: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='attributes',
                data=attributes,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat attributes: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer attributes: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR attributes: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class ConstantsService(BaseMetadataService):
    """Service de synchronisation des constantes"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les constantes"""
        try:
            if job:
                job.log_message += "Synchronisation de constants...\n"
                job.save()

            constants = self.source_instance.get_metadata(
                resource='constants',
                fields='id,name,displayName,code,description,value',
                paging=False
            )

            if not constants:
                if job:
                    job.log_message += "Resultat constants: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='constants',
                data=constants,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat constants: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer constants: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR constants: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class SystemSyncService:
    """
    Service orchestrateur pour la synchronisation des attributs et constantes
    Respecte l'ordre DHIS2: attributes -> constants
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.attributes_service = AttributesService(self.source, self.dest)
        self.constants_service = ConstantsService(self.source, self.dest)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements systeme dans l'ordre correct

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

            # 1. attributes (obligatoire en premier)
            attributes_result = self.attributes_service.sync(job, strategy)
            results['attributes'] = attributes_result
            total_imported += attributes_result.get('imported_count', 0)
            if not attributes_result.get('success', False):
                total_errors += 1

            # 2. constants
            constants_result = self.constants_service.sync(job, strategy)
            results['constants'] = constants_result
            total_imported += constants_result.get('imported_count', 0)
            if not constants_result.get('success', False):
                total_errors += 1

            return {
                'success': total_errors == 0,
                'results': results,
                'total_imported': total_imported,
                'total_errors': total_errors
            }

        except Exception as e:
            error_msg = f"Erreur lors de la synchronisation des elements systeme: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}