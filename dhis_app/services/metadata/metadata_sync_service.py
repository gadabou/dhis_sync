"""
Service principal de synchronisation des métadonnées DHIS2
"""
import logging
from typing import Dict, List, Any, Optional
from django.utils import timezone
from .base import BaseMetadataService, MetadataServiceError
from .users import UsersSyncService
from .orgUnits import OrganisationUnitsSyncService
from .categories import CategoriesSyncService
from .dataElements import DataElementsSyncService
from .options import OptionsSyncService
from .indicators import IndicatorsSyncService
from .dataSets import DataSetsSyncService
from .tracker import TrackerSyncService
from .programs import ProgramsSyncService
from .validation import ValidationSyncService
from .predictors import PredictorsSyncService
from .legends import LegendsSyncService
from .system import SystemSyncService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class MetadataSyncService(BaseMetadataService):
    """Service de synchronisation des métadonnées DHIS2"""

    def sync_all_metadata(self, job: SyncJob, families: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Synchronise toutes les métadonnées selon l'ordre défini

        Args:
            job: Job de synchronisation
            families: Familles à synchroniser (toutes si None)

        Returns:
            Résultat de la synchronisation
        """
        try:
            job.status = 'running'
            job.started_at = timezone.now()
            job.log_message += "=== DÉBUT SYNCHRONISATION MÉTADONNÉES ===\n"
            job.save()

            # Vérifier la compatibilité
            compatibility = self.check_instances_compatibility()
            if not compatibility['compatible']:
                error_msg = "Instances incompatibles: " + "; ".join(compatibility['errors'])
                job.status = 'failed'
                job.log_message += f"ERREUR: {error_msg}\n"
                job.save()
                return {'success': False, 'error': error_msg}

            # Résoudre les dépendances
            if families:
                families = self.validate_dependencies(families)
            else:
                families = list(self.METADATA_FAMILIES_CONFIG.keys())

            job.log_message += f"Familles à synchroniser: {', '.join(families)}\n"
            job.save()

            # Synchroniser par famille dans l'ordre
            results = {}
            total_imported = 0
            total_errors = 0

            for family_name in families:
                try:
                    family_result = self.sync_metadata_family(job, family_name)
                    results[family_name] = family_result

                    total_imported += family_result.get('imported_count', 0)
                    total_errors += family_result.get('error_count', 0)

                    # Mettre à jour le progrès
                    progress = (len(results) / len(families)) * 100
                    job.progress = int(progress)
                    job.save()

                except Exception as e:
                    error_msg = f"Erreur critique famille {family_name}: {str(e)}"
                    self.logger.error(error_msg)
                    job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                    total_errors += 1
                    results[family_name] = {'success': False, 'error': str(e)}

            # Finaliser le job
            job.completed_at = timezone.now()
            job.progress = 100

            if total_errors == 0:
                job.status = 'completed'
                job.log_message += f"=== SYNCHRONISATION RÉUSSIE - {total_imported} éléments importés ===\n"
            elif total_errors < len(families):
                job.status = 'completed_with_warnings'
                job.log_message += f"=== SYNCHRONISATION TERMINÉE AVEC AVERTISSEMENTS - {total_imported} éléments importés, {total_errors} erreurs ===\n"
            else:
                job.status = 'failed'
                job.log_message += f"=== SYNCHRONISATION ÉCHOUÉE - {total_errors} erreurs critiques ===\n"

            job.save()

            return {
                'success': total_errors < len(families),
                'results': results,
                'total_imported': total_imported,
                'total_errors': total_errors
            }

        except Exception as e:
            error_msg = f"Erreur critique lors de la synchronisation des métadonnées: {str(e)}"
            self.logger.error(error_msg)

            job.status = 'failed'
            job.completed_at = timezone.now()
            job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
            job.save()

            return {'success': False, 'error': error_msg}

    def sync_metadata_family(self, job: SyncJob, family_name: str) -> Dict[str, Any]:
        """
        Synchronise une famille complète de métadonnées

        Args:
            job: Job de synchronisation
            family_name: Nom de la famille

        Returns:
            Résultat de la synchronisation de la famille
        """
        try:
            family_config = self.METADATA_FAMILIES_CONFIG.get(family_name)
            if not family_config:
                raise MetadataServiceError(f"Famille inconnue: {family_name}")

            job.log_message += f"\n--- FAMILLE: {family_config['description']} ---\n"
            job.save()

            # Traitement spécial pour la famille "users"
            if family_name == 'users':
                return self._sync_users_family(job)

            # Traitement spécial pour la famille "organisation"
            if family_name == 'organisation':
                return self._sync_organisation_family(job)

            # Traitement spécial pour la famille "categories"
            if family_name == 'categories':
                return self._sync_categories_family(job)

            # Traitement spécial pour la famille "data_elements"
            if family_name == 'data_elements':
                return self._sync_data_elements_family(job)

            # Traitement spécial pour la famille "options"
            if family_name == 'options':
                return self._sync_options_family(job)

            # Traitement spécial pour la famille "indicators"
            if family_name == 'indicators':
                return self._sync_indicators_family(job)

            # Traitement spécial pour la famille "data_sets"
            if family_name == 'data_sets':
                return self._sync_data_sets_family(job)

            # Traitement spécial pour la famille "tracker"
            if family_name == 'tracker':
                return self._sync_tracker_family(job)

            # Traitement spécial pour la famille "programs"
            if family_name == 'programs':
                return self._sync_programs_family(job)

            # Traitement spécial pour la famille "validation"
            if family_name == 'validation':
                return self._sync_validation_family(job)

            # Traitement spécial pour la famille "predictors"
            if family_name == 'predictors':
                return self._sync_predictors_family(job)

            # Traitement spécial pour la famille "legends"
            if family_name == 'legends':
                return self._sync_legends_family(job)

            # Traitement spécial pour la famille "system"
            if family_name == 'system':
                return self._sync_system_family(job)

            # Traitement standard pour les autres familles
            resources = family_config['resources']
            job.log_message += f"Ressources: {', '.join(resources)}\n"
            job.save()

            # Synchroniser chaque ressource dans l'ordre
            family_results = {}
            total_imported = 0
            total_errors = 0

            # Ordonner les ressources selon IMPORT_ORDER
            ordered_resources = sorted(resources, key=lambda x: self.IMPORT_ORDER.get(x, 999))

            for resource in ordered_resources:
                try:
                    result = self.sync_metadata_resource(
                        resource=resource,
                        job=job,
                        strategy=job.sync_config.import_strategy
                    )

                    family_results[resource] = result
                    total_imported += result.get('imported_count', 0)
                    if not result['success']:
                        total_errors += 1

                except Exception as e:
                    error_msg = f"Erreur ressource {resource}: {str(e)}"
                    self.logger.error(error_msg)
                    family_results[resource] = {'success': False, 'error': str(e)}
                    total_errors += 1

            job.log_message += f"Famille {family_name}: {total_imported} éléments, {total_errors} erreurs\n"
            job.save()

            return {
                'success': total_errors == 0,
                'imported_count': total_imported,
                'error_count': total_errors,
                'resources': family_results
            }

        except Exception as e:
            error_msg = f"Erreur famille {family_name}: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR famille {family_name}: {error_msg}\n"
            job.save()

            return {'success': False, 'error': error_msg}

    def _sync_users_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille des utilisateurs en utilisant le service spécialisé

        Args:
            job: Job de synchronisation

        Returns:
            Résultat de la synchronisation
        """
        try:
            # Créer le service avec la configuration du job
            users_service = UsersSyncService(job.sync_config)

            # Synchroniser dans l'ordre: userRoles -> users -> userGroups
            result = users_service.sync_all(job)

            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille users: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_organisation_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille des unités d'organisation en utilisant le service spécialisé

        Args:
            job: Job de synchronisation

        Returns:
            Résultat de la synchronisation
        """
        try:
            # Créer le service avec la configuration du job
            org_units_service = OrganisationUnitsSyncService(job.sync_config)

            # Synchroniser dans l'ordre: organisationUnitLevels -> organisationUnits -> organisationUnitGroups -> organisationUnitGroupSets
            result = org_units_service.sync_all(job)

            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille organisation: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_categories_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille des categories en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            categories_service = CategoriesSyncService(job.sync_config)
            result = categories_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille categories: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_data_elements_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille des elements de donnees en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            data_elements_service = DataElementsSyncService(job.sync_config)
            result = data_elements_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille data_elements: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_options_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille des options en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            options_service = OptionsSyncService(job.sync_config)
            result = options_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille options: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_indicators_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille des indicateurs en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            indicators_service = IndicatorsSyncService(job.sync_config)
            result = indicators_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille indicators: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_data_sets_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille des ensembles de donnees en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            data_sets_service = DataSetsSyncService(job.sync_config)
            result = data_sets_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille data_sets: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_tracker_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille tracker en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            tracker_service = TrackerSyncService(job.sync_config)
            result = tracker_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille tracker: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_programs_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille des programmes en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            programs_service = ProgramsSyncService(job.sync_config)
            result = programs_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille programs: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_validation_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille validation en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            validation_service = ValidationSyncService(job.sync_config)
            result = validation_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille validation: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_predictors_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille predictors en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            predictors_service = PredictorsSyncService(job.sync_config)
            result = predictors_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille predictors: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_legends_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille legends en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            legends_service = LegendsSyncService(job.sync_config)
            result = legends_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille legends: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def _sync_system_family(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise la famille system en utilisant le service specialise

        Args:
            job: Job de synchronisation

        Returns:
            Resultat de la synchronisation
        """
        try:
            system_service = SystemSyncService(job.sync_config)
            result = system_service.sync_all(job)
            return result

        except Exception as e:
            error_msg = f"Erreur synchronisation famille system: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR: {error_msg}\n"
            job.save()
            return {'success': False, 'error': error_msg}

    def sync_specific_resources(self, job: SyncJob, resources: List[str]) -> Dict[str, Any]:
        """
        Synchronise des ressources spécifiques

        Args:
            job: Job de synchronisation
            resources: Liste des ressources à synchroniser

        Returns:
            Résultat de la synchronisation
        """
        try:
            job.status = 'running'
            job.started_at = timezone.now()
            job.log_message += f"=== SYNCHRONISATION RESSOURCES SPÉCIFIQUES ===\n"
            job.log_message += f"Ressources: {', '.join(resources)}\n"
            job.save()

            # Vérifier la compatibilité
            compatibility = self.check_instances_compatibility()
            if not compatibility['compatible']:
                error_msg = "Instances incompatibles: " + "; ".join(compatibility['errors'])
                job.status = 'failed'
                job.log_message += f"ERREUR: {error_msg}\n"
                job.save()
                return {'success': False, 'error': error_msg}

            # Trier les ressources par ordre d'import
            ordered_resources = sorted(resources, key=lambda x: self.IMPORT_ORDER.get(x, 999))

            results = {}
            total_imported = 0
            total_errors = 0

            for i, resource in enumerate(ordered_resources):
                try:
                    result = self.sync_metadata_resource(
                        resource=resource,
                        job=job,
                        strategy=job.sync_config.import_strategy
                    )

                    results[resource] = result
                    total_imported += result.get('imported_count', 0)
                    if not result['success']:
                        total_errors += 1

                    # Mettre à jour le progrès
                    progress = ((i + 1) / len(ordered_resources)) * 100
                    job.progress = int(progress)
                    job.save()

                except Exception as e:
                    error_msg = f"Erreur ressource {resource}: {str(e)}"
                    self.logger.error(error_msg)
                    results[resource] = {'success': False, 'error': str(e)}
                    total_errors += 1

            # Finaliser le job
            job.completed_at = timezone.now()
            job.progress = 100

            if total_errors == 0:
                job.status = 'completed'
                job.log_message += f"=== SYNCHRONISATION RÉUSSIE - {total_imported} éléments importés ===\n"
            elif total_errors < len(ordered_resources):
                job.status = 'completed_with_warnings'
                job.log_message += f"=== SYNCHRONISATION TERMINÉE AVEC AVERTISSEMENTS - {total_imported} éléments importés, {total_errors} erreurs ===\n"
            else:
                job.status = 'failed'
                job.log_message += f"=== SYNCHRONISATION ÉCHOUÉE - {total_errors} erreurs critiques ===\n"

            job.save()

            return {
                'success': total_errors < len(ordered_resources),
                'results': results,
                'total_imported': total_imported,
                'total_errors': total_errors
            }

        except Exception as e:
            error_msg = f"Erreur critique lors de la synchronisation des ressources: {str(e)}"
            self.logger.error(error_msg)

            job.status = 'failed'
            job.completed_at = timezone.now()
            job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
            job.save()

            return {'success': False, 'error': error_msg}

    def get_available_families(self) -> Dict[str, Dict[str, Any]]:
        """
        Retourne la liste des familles de métadonnées disponibles

        Returns:
            Dictionnaire des familles avec leurs informations
        """
        return self.METADATA_FAMILIES_CONFIG.copy()

    def get_family_resources(self, family_name: str) -> List[str]:
        """
        Retourne la liste des ressources d'une famille

        Args:
            family_name: Nom de la famille

        Returns:
            Liste des ressources de la famille
        """
        family_config = self.METADATA_FAMILIES_CONFIG.get(family_name)
        return family_config['resources'] if family_config else []