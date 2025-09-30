"""
Service de synchronisation des regles de validation DHIS2
Respecte l'ordre d'importation DHIS2: validationRules -> validationRuleGroups -> validationNotificationTemplates
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class ValidationRulesService(BaseMetadataService):
    """Service de synchronisation des regles de validation"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les regles de validation"""
        try:
            if job:
                job.log_message += "Synchronisation de validationRules...\n"
                job.save()

            rules = self.source_instance.get_metadata(
                resource='validationRules',
                fields='id,name,displayName,code,description,instruction,importance,operator,periodType,skipFormValidation,leftSide[expression,description,missingValueStrategy],rightSide[expression,description,missingValueStrategy],organisationUnitLevels',
                paging=False
            )

            if not rules:
                if job:
                    job.log_message += "Resultat validationRules: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='validationRules',
                data=rules,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat validationRules: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer validationRules: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR validationRules: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class ValidationRuleGroupsService(BaseMetadataService):
    """Service de synchronisation des groupes de regles de validation"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les groupes de regles de validation"""
        try:
            if job:
                job.log_message += "Synchronisation de validationRuleGroups...\n"
                job.save()

            groups = self.source_instance.get_metadata(
                resource='validationRuleGroups',
                fields='id,name,displayName,code,description,validationRules[id]',
                paging=False
            )

            if not groups:
                if job:
                    job.log_message += "Resultat validationRuleGroups: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='validationRuleGroups',
                data=groups,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat validationRuleGroups: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer validationRuleGroups: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR validationRuleGroups: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class ValidationSyncService:
    """
    Service orchestrateur pour la synchronisation des regles de validation
    Respecte l'ordre DHIS2: validationRules -> validationRuleGroups
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.rules_service = ValidationRulesService(self.source, self.dest)
        self.groups_service = ValidationRuleGroupsService(self.source, self.dest)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux regles de validation dans l'ordre correct

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

            # 1. validationRules (obligatoire en premier)
            rules_result = self.rules_service.sync(job, strategy)
            results['validationRules'] = rules_result
            total_imported += rules_result.get('imported_count', 0)
            if not rules_result.get('success', False):
                total_errors += 1

            # 2. validationRuleGroups (necessite validationRules)
            groups_result = self.groups_service.sync(job, strategy)
            results['validationRuleGroups'] = groups_result
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
            error_msg = f"Erreur lors de la synchronisation des regles de validation: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}