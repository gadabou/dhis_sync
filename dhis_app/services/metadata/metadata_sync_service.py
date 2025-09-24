"""
Service principal de synchronisation des métadonnées DHIS2
"""
import logging
from typing import Dict, List, Any, Optional
from django.utils import timezone
from .base import BaseMetadataService, MetadataServiceError
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

            resources = family_config['resources']
            job.log_message += f"\n--- FAMILLE: {family_config['description']} ---\n"
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