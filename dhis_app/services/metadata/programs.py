"""
Service de synchronisation des programmes DHIS2
Respecte l'ordre d'importation DHIS2: programs -> programStages -> programStageSections -> programRuleVariables -> programRules -> programRuleActions -> programIndicators -> programNotificationTemplates
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class ProgramsService(BaseMetadataService):
    """Service de synchronisation des programmes"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les programmes"""
        try:
            if job:
                job.log_message += "Synchronisation de programs...\n"
                job.save()

            programs = self.source_instance.get_metadata(
                resource='programs',
                fields='id,name,displayName,code,description,version,programType,trackedEntityType[id],categoryCombo[id],organisationUnits[id],programStages[id],programTrackedEntityAttributes[id,trackedEntityAttribute[id],mandatory,displayInList,sortOrder],withoutRegistration,captureCoordinates,useFirstStageDuringRegistration,displayFrontPageList,programIndicators[id],completeEventsExpiryDays,displayIncidentDate,incidentDateLabel,enrollmentDateLabel,ignoreOverdueEvents,selectIncidentDatesInFuture,selectEnrollmentDatesInFuture,onlyEnrollOnce,dataEntryMethod,minAttributesRequiredToSearch,maxTeiCountToReturn,accessLevel',
                paging=False
            )

            if not programs:
                if job:
                    job.log_message += "Resultat programs: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='programs',
                data=programs,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat programs: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': True,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer programs: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR programs: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class ProgramStagesService(BaseMetadataService):
    """Service de synchronisation des etapes de programmes"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les etapes de programmes"""
        try:
            if job:
                job.log_message += "Synchronisation de programStages...\n"
                job.save()

            stages = self.source_instance.get_metadata(
                resource='programStages',
                fields='id,name,displayName,description,sortOrder,program[id],minDaysFromStart,repeatable,periodType,displayGenerateEventBox,standardInterval,executionDateLabel,dueDateLabel,autoGenerateEvent,validationStrategy,blockEntryForm,preGenerateUID,remindCompleted,generatedByEnrollmentDate,allowGenerateNextVisit,openAfterEnrollment,reportDateToUse,hideDueDate,programStageDataElements[id,dataElement[id],compulsory,allowProvidedElsewhere,displayInReports,sortOrder],programStageSections[id]',
                paging=False
            )

            if not stages:
                if job:
                    job.log_message += "Resultat programStages: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='programStages',
                data=stages,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat programStages: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer programStages: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR programStages: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class ProgramRuleVariablesService(BaseMetadataService):
    """Service de synchronisation des variables de regles de programmes"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les variables de regles de programmes"""
        try:
            if job:
                job.log_message += "Synchronisation de programRuleVariables...\n"
                job.save()

            variables = self.source_instance.get_metadata(
                resource='programRuleVariables',
                fields='id,name,displayName,program[id],programStage[id],dataElement[id],trackedEntityAttribute[id],sourceType,useCodeForOptionSet,valueType',
                paging=False
            )

            if not variables:
                if job:
                    job.log_message += "Resultat programRuleVariables: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='programRuleVariables',
                data=variables,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat programRuleVariables: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer programRuleVariables: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR programRuleVariables: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class ProgramRulesService(BaseMetadataService):
    """Service de synchronisation des regles de programmes"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les regles de programmes"""
        try:
            if job:
                job.log_message += "Synchronisation de programRules...\n"
                job.save()

            rules = self.source_instance.get_metadata(
                resource='programRules',
                fields='id,name,displayName,description,program[id],programStage[id],condition,priority,programRuleActions[id]',
                paging=False
            )

            if not rules:
                if job:
                    job.log_message += "Resultat programRules: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='programRules',
                data=rules,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat programRules: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer programRules: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR programRules: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class ProgramRuleActionsService(BaseMetadataService):
    """Service de synchronisation des actions de regles de programmes"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les actions de regles de programmes"""
        try:
            if job:
                job.log_message += "Synchronisation de programRuleActions...\n"
                job.save()

            actions = self.source_instance.get_metadata(
                resource='programRuleActions',
                fields='id,programRuleActionType,programRule[id],dataElement[id],trackedEntityAttribute[id],programStage[id],programStageSection[id],content,data,location',
                paging=False
            )

            if not actions:
                if job:
                    job.log_message += "Resultat programRuleActions: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='programRuleActions',
                data=actions,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat programRuleActions: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer programRuleActions: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR programRuleActions: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class ProgramIndicatorsService(BaseMetadataService):
    """Service de synchronisation des indicateurs de programmes"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les indicateurs de programmes"""
        try:
            if job:
                job.log_message += "Synchronisation de programIndicators...\n"
                job.save()

            indicators = self.source_instance.get_metadata(
                resource='programIndicators',
                fields='id,name,displayName,code,description,program[id],expression,filter,aggregationType,analyticsType,decimals',
                paging=False
            )

            if not indicators:
                if job:
                    job.log_message += "Resultat programIndicators: 0 importes, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='programIndicators',
                data=indicators,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Resultat programIndicators: {stats.get('imported', 0)} importes, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer programIndicators: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR programIndicators: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class ProgramsSyncService:
    """
    Service orchestrateur pour la synchronisation des programmes
    Respecte l'ordre DHIS2: programs -> programStages -> programRuleVariables -> programRules -> programRuleActions -> programIndicators
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.programs_service = ProgramsService(self.source, self.dest)
        self.stages_service = ProgramStagesService(self.source, self.dest)
        self.rule_variables_service = ProgramRuleVariablesService(self.source, self.dest)
        self.rules_service = ProgramRulesService(self.source, self.dest)
        self.rule_actions_service = ProgramRuleActionsService(self.source, self.dest)
        self.indicators_service = ProgramIndicatorsService(self.source, self.dest)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les elements lies aux programmes dans l'ordre correct

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

            # 1. programs (obligatoire en premier)
            programs_result = self.programs_service.sync(job, strategy)
            results['programs'] = programs_result
            total_imported += programs_result.get('imported_count', 0)
            if not programs_result.get('success', False):
                total_errors += 1

            # 2. programStages (necessite programs)
            stages_result = self.stages_service.sync(job, strategy)
            results['programStages'] = stages_result
            total_imported += stages_result.get('imported_count', 0)
            if not stages_result.get('success', False):
                total_errors += 1

            # 3. programRuleVariables (necessite programs et programStages)
            variables_result = self.rule_variables_service.sync(job, strategy)
            results['programRuleVariables'] = variables_result
            total_imported += variables_result.get('imported_count', 0)
            if not variables_result.get('success', False):
                total_errors += 1

            # 4. programRules (necessite programRuleVariables)
            rules_result = self.rules_service.sync(job, strategy)
            results['programRules'] = rules_result
            total_imported += rules_result.get('imported_count', 0)
            if not rules_result.get('success', False):
                total_errors += 1

            # 5. programRuleActions (necessite programRules)
            actions_result = self.rule_actions_service.sync(job, strategy)
            results['programRuleActions'] = actions_result
            total_imported += actions_result.get('imported_count', 0)
            if not actions_result.get('success', False):
                total_errors += 1

            # 6. programIndicators (necessite programs)
            indicators_result = self.indicators_service.sync(job, strategy)
            results['programIndicators'] = indicators_result
            total_imported += indicators_result.get('imported_count', 0)
            if not indicators_result.get('success', False):
                total_errors += 1

            return {
                'success': total_errors == 0,
                'results': results,
                'total_imported': total_imported,
                'total_errors': total_errors
            }

        except Exception as e:
            error_msg = f"Erreur lors de la synchronisation des programmes: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}