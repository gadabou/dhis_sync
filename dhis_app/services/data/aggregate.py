"""
Service de synchronisation des données agrégées DHIS2
"""
import logging
from typing import Dict, List, Any, Optional
from django.utils import timezone
from .base import BaseDataService, DataServiceError
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class AggregateDataService(BaseDataService):
    """Service de synchronisation des données agrégées DHIS2"""

    def sync_aggregate_data(self, job: SyncJob, org_units: Optional[List[str]] = None,
                           periods: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Synchronise les données agrégées

        Args:
            job: Job de synchronisation
            org_units: Liste des UIDs d'unités d'organisation (optionnel)
            periods: Liste des périodes à synchroniser (optionnel)

        Returns:
            Résultat de la synchronisation
        """
        try:
            job.status = 'running'
            job.started_at = timezone.now()
            job.log_message += "=== DÉBUT SYNCHRONISATION DONNÉES AGRÉGÉES ===\n"
            job.save()

            # Vérifier la compatibilité
            compatibility = self.check_instances_compatibility()
            if not compatibility['compatible']:
                error_msg = "Instances incompatibles: " + "; ".join(compatibility['errors'])
                job.status = 'failed'
                job.log_message += f"ERREUR: {error_msg}\n"
                job.save()
                return {'success': False, 'error': error_msg}

            # Obtenir les paramètres de synchronisation
            sync_config = job.sync_config
            date_range = self.get_date_range_from_config(sync_config)

            # Construire les paramètres de récupération
            params = self._build_data_params(
                org_units=org_units,
                periods=periods,
                date_range=date_range,
                config=sync_config
            )

            job.log_message += f"Paramètres: {params}\n"
            job.save()

            # Récupérer les données agrégées
            job.log_message += "Récupération des données agrégées...\n"
            data_values = self.fetch_aggregate_data(params)

            source_count = len(data_values) if data_values else 0

            if not data_values:
                job.status = 'completed'
                job.log_message += self._format_sync_log('dataValues', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'deleted': 0, 'errors': 0})
                job.save()
                return {'success': True, 'imported_count': 0, 'message': 'Aucune donnée à synchroniser'}

            job.total_items = len(data_values)
            job.log_message += f"Trouvé {len(data_values)} valeurs de données\n"
            job.save()

            # Importer les données
            result = self.import_aggregate_data(data_values, job)

            # Analyser les résultats
            stats = self._analyze_import_result(result)

            # Finaliser le job
            job.processed_items = len(data_values)
            job.success_count = stats.get('imported', 0) + stats.get('updated', 0)
            job.error_count = stats.get('errors', 0)
            job.completed_at = timezone.now()
            job.progress = 100

            # Log détaillé
            job.log_message += self._format_sync_log('dataValues', source_count, stats)

            if stats.get('errors', 0) == 0:
                job.status = 'completed'
                job.log_message += f"=== SYNCHRONISATION RÉUSSIE ===\n"
            else:
                job.status = 'completed_with_warnings'
                job.log_message += f"=== SYNCHRONISATION TERMINÉE AVEC AVERTISSEMENTS ===\n"

            job.save()

            return {
                'success': True,
                'imported_count': stats.get('imported', 0),
                'updated_count': stats.get('updated', 0),
                'error_count': stats.get('errors', 0),
                'result': result
            }

        except Exception as e:
            error_msg = f"Erreur critique lors de la synchronisation des données agrégées: {str(e)}"
            self.logger.error(error_msg)

            job.status = 'failed'
            job.completed_at = timezone.now()
            job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
            job.save()

            return {'success': False, 'error': error_msg}

    def fetch_aggregate_data(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Récupère les données agrégées depuis l'instance source

        Args:
            params: Paramètres de récupération

        Returns:
            Liste des valeurs de données
        """
        try:
            self.logger.info("Récupération des données agrégées")

            # Utiliser l'API dataValueSets pour récupérer les données
            api = self.source_instance.get_api_client()

            # Construire les paramètres pour l'API
            api_params = {}

            if params.get('orgUnits'):
                api_params['orgUnit'] = params['orgUnits']

            if params.get('periods'):
                api_params['period'] = params['periods']

            if params.get('startDate'):
                api_params['startDate'] = params['startDate']

            if params.get('endDate'):
                api_params['endDate'] = params['endDate']

            if params.get('dataElements'):
                api_params['dataElement'] = params['dataElements']

            if params.get('dataSet'):
                api_params['dataSet'] = params['dataSet']

            # Ajouter la pagination
            api_params['paging'] = 'false'  # Récupérer toutes les données

            response = api.get('dataValueSets', params=api_params)
            response.raise_for_status()

            data = response.json()
            data_values = data.get('dataValues', [])

            self.logger.info(f"Récupérés {len(data_values)} valeurs de données agrégées")
            return data_values

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des données agrégées: {e}")
            raise DataServiceError(f"Impossible de récupérer les données agrégées: {str(e)}")

    def import_aggregate_data(self, data_values: List[Dict[str, Any]], job: Optional[SyncJob] = None) -> Dict[str, Any]:
        """
        Importe les données agrégées vers l'instance destination

        Args:
            data_values: Valeurs de données à importer
            job: Job de synchronisation (optionnel)

        Returns:
            Résultat de l'import
        """
        try:
            if not data_values:
                return {'status': 'OK', 'message': 'Aucune donnée à importer'}

            self.logger.info(f"Import de {len(data_values)} valeurs de données agrégées")

            # Diviser en chunks pour éviter les timeouts
            chunks = self.chunk_data(data_values, chunk_size=1000)
            total_results = []

            for i, chunk in enumerate(chunks):
                if job:
                    job.log_message += f"Import chunk {i+1}/{len(chunks)} ({len(chunk)} valeurs)...\n"
                    job.save()

                try:
                    result = self.destination_instance.import_data_values(
                        data_values=chunk,
                        dry_run=False,
                        atomic_mode='NONE'  # Continuer même en cas d'erreurs partielles
                    )

                    total_results.append(result)

                    # Mettre à jour le progrès
                    if job:
                        progress = ((i + 1) / len(chunks)) * 100
                        job.progress = int(progress * 0.8)  # 80% pour l'import, 20% pour la finalisation
                        job.save()

                except Exception as e:
                    error_msg = f"Erreur import chunk {i+1}: {str(e)}"
                    self.logger.error(error_msg)
                    if job:
                        job.log_message += f"ERREUR: {error_msg}\n"
                        job.save()

                    # Continuer avec les autres chunks
                    total_results.append({
                        'status': 'ERROR',
                        'message': str(e),
                        'conflicts': [{'object': f'chunk_{i+1}', 'value': str(e)}]
                    })

            # Consolider les résultats
            consolidated_result = self._consolidate_import_results(total_results)

            self.logger.info(f"Import terminé: {consolidated_result.get('status', 'Unknown')}")
            return consolidated_result

        except Exception as e:
            self.logger.error(f"Erreur lors de l'import des données agrégées: {e}")
            raise DataServiceError(f"Impossible d'importer les données agrégées: {str(e)}")

    def _build_data_params(self, org_units: Optional[List[str]] = None,
                          periods: Optional[List[str]] = None,
                          date_range: Optional[Dict[str, str]] = None,
                          config: Optional[SyncConfiguration] = None) -> Dict[str, Any]:
        """
        Construit les paramètres pour la récupération des données

        Args:
            org_units: Liste des unités d'organisation
            periods: Liste des périodes
            date_range: Plage de dates
            config: Configuration de synchronisation

        Returns:
            Paramètres formatés
        """
        params = {}

        # Unités d'organisation (obligatoire pour DHIS2)
        if org_units:
            valid_org_units = self.validate_org_units(org_units)
            if valid_org_units:
                params['orgUnits'] = valid_org_units
        else:
            # Si aucune unité n'est spécifiée, récupérer toutes les unités
            try:
                all_org_units = self.source_instance.get_metadata(
                    resource='organisationUnits',
                    fields='id',
                    paging=False
                )
                if all_org_units:
                    # Limiter aux 10 premières unités pour éviter une requête trop large
                    params['orgUnits'] = [ou['id'] for ou in all_org_units[:10]]
                    self.logger.warning(f"Aucune unité d'organisation spécifiée. Utilisation des {len(params['orgUnits'])} premières unités.")
            except Exception as e:
                self.logger.error(f"Impossible de récupérer les unités d'organisation: {e}")
                # Pas d'unités = erreur
                raise DataServiceError("Au moins une unité d'organisation doit être spécifiée pour synchroniser les données agrégées")

        # Périodes
        if periods:
            valid_periods = self.validate_periods(periods)
            if valid_periods:
                params['periods'] = valid_periods

        # Plage de dates (alternative aux périodes)
        if date_range and not periods:
            if date_range.get('start_date'):
                params['startDate'] = date_range['start_date']
            if date_range.get('end_date'):
                params['endDate'] = date_range['end_date']

        # Éléments de données (obligatoire pour DHIS2)
        # Récupérer tous les dataSets disponibles
        try:
            all_datasets = self.source_instance.get_metadata(
                resource='dataSets',
                fields='id',
                paging=False
            )
            if all_datasets:
                params['dataSet'] = [ds['id'] for ds in all_datasets]
                self.logger.info(f"Récupération des données pour {len(params['dataSet'])} dataSets")
            else:
                # Si aucun dataSet, essayer avec tous les dataElements
                self.logger.warning("Aucun dataSet trouvé, récupération de tous les dataElements")
                all_data_elements = self.source_instance.get_metadata(
                    resource='dataElements',
                    fields='id',
                    paging=False
                )
                if all_data_elements:
                    params['dataElements'] = [de['id'] for de in all_data_elements]
                    self.logger.info(f"Récupération des données pour {len(params['dataElements'])} dataElements")
                else:
                    raise DataServiceError("Aucun dataSet ou dataElement trouvé pour synchroniser les données agrégées")
        except Exception as e:
            self.logger.error(f"Impossible de récupérer les dataSets/dataElements: {e}")
            raise DataServiceError(f"Au moins un dataSet ou dataElement doit être disponible pour synchroniser les données agrégées: {str(e)}")

        return params

    def _consolidate_import_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Consolide les résultats de plusieurs imports

        Args:
            results: Liste des résultats d'import

        Returns:
            Résultat consolidé
        """
        consolidated = {
            'status': 'OK',
            'response': {
                'importCount': {
                    'imported': 0,
                    'updated': 0,
                    'ignored': 0,
                    'deleted': 0
                },
                'conflicts': []
            }
        }

        total_errors = 0

        for result in results:
            try:
                if 'response' in result:
                    response = result['response']
                    import_count = response.get('importCount', {})

                    consolidated['response']['importCount']['imported'] += import_count.get('imported', 0)
                    consolidated['response']['importCount']['updated'] += import_count.get('updated', 0)
                    consolidated['response']['importCount']['ignored'] += import_count.get('ignored', 0)
                    consolidated['response']['importCount']['deleted'] += import_count.get('deleted', 0)

                    conflicts = response.get('conflicts', [])
                    consolidated['response']['conflicts'].extend(conflicts)
                    total_errors += len(conflicts)

                elif result.get('status') == 'ERROR':
                    total_errors += 1
                    consolidated['response']['conflicts'].append({
                        'object': 'import_chunk',
                        'value': result.get('message', 'Erreur inconnue')
                    })

            except Exception as e:
                self.logger.warning(f"Erreur consolidation résultat: {e}")
                total_errors += 1

        # Déterminer le statut global
        if total_errors > 0:
            if total_errors == len(results):
                consolidated['status'] = 'ERROR'
            else:
                consolidated['status'] = 'WARNING'

        return consolidated