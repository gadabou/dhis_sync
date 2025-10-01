"""
Service de base pour la synchronisation des données DHIS2
"""
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from django.utils import timezone
from ...models import DHIS2Instance, SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class DataServiceError(Exception):
    """Exception personnalisée pour les services de données"""
    pass


class BaseDataService:
    """Service de base pour la synchronisation des données DHIS2"""

    def __init__(self, source_instance: DHIS2Instance, destination_instance: DHIS2Instance):
        """
        Initialise le service de données

        Args:
            source_instance: Instance DHIS2 source
            destination_instance: Instance DHIS2 destination
        """
        self.source_instance = source_instance
        self.destination_instance = destination_instance
        self.logger = logger

    def check_instances_compatibility(self) -> Dict[str, Any]:
        """
        Vérifie la compatibilité entre les instances source et destination

        Returns:
            Dictionnaire avec les résultats de compatibilité
        """
        try:
            # Test de connexion source
            source_test = self.source_instance.test_connection()

            # Test de connexion destination
            dest_test = self.destination_instance.test_connection()

            compatibility = {
                'source_available': source_test['success'],
                'dest_available': dest_test['success'],
                'source_version': source_test.get('dhis2_version'),
                'dest_version': dest_test.get('dhis2_version'),
                'compatible': True,
                'warnings': [],
                'errors': []
            }

            if not source_test['success']:
                compatibility['errors'].append(f"Instance source inaccessible: {source_test['message']}")
                compatibility['compatible'] = False

            if not dest_test['success']:
                compatibility['errors'].append(f"Instance destination inaccessible: {dest_test['message']}")
                compatibility['compatible'] = False

            return compatibility

        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de compatibilité: {e}")
            return {
                'source_available': False,
                'dest_available': False,
                'compatible': False,
                'errors': [str(e)]
            }

    def format_date_for_api(self, date_obj: Union[datetime, date, str, None]) -> Optional[str]:
        """
        Formate une date pour l'API DHIS2

        Args:
            date_obj: Objet date à formater

        Returns:
            Date formatée pour DHIS2 (YYYY-MM-DD) ou None
        """
        if not date_obj:
            return None

        try:
            if isinstance(date_obj, str):
                # Tenter de parser la chaîne
                try:
                    parsed_date = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    return date_obj  # Retourner tel quel si déjà au bon format

            elif isinstance(date_obj, datetime):
                return date_obj.strftime('%Y-%m-%d')

            elif isinstance(date_obj, date):
                return date_obj.strftime('%Y-%m-%d')

            return str(date_obj)

        except Exception as e:
            self.logger.warning(f"Erreur formatage date {date_obj}: {e}")
            return None

    def get_date_range_from_config(self, sync_config: SyncConfiguration) -> Dict[str, Optional[str]]:
        """
        Extrait la plage de dates de synchronisation depuis la configuration

        Args:
            sync_config: Configuration de synchronisation

        Returns:
            Dictionnaire avec start_date et end_date
        """
        return {
            'start_date': self.format_date_for_api(sync_config.sync_start_date),
            'end_date': self.format_date_for_api(sync_config.sync_end_date)
        }

    def _analyze_import_result(self, result: Dict[str, Any]) -> Dict[str, int]:
        """
        Analyse le résultat d'un import DHIS2 pour extraire les statistiques

        Args:
            result: Résultat de l'import DHIS2

        Returns:
            Statistiques extraites
        """
        stats = {'imported': 0, 'updated': 0, 'ignored': 0, 'deleted': 0, 'errors': 0}

        try:
            # Structure typique de réponse DHIS2 pour les données
            if 'response' in result:
                response = result['response']

                # Pour les données agrégées
                if 'importCount' in response:
                    stats['imported'] = response.get('importCount', {}).get('imported', 0)
                    stats['updated'] = response.get('importCount', {}).get('updated', 0)
                    stats['ignored'] = response.get('importCount', {}).get('ignored', 0)
                    stats['deleted'] = response.get('importCount', {}).get('deleted', 0)

                # Compter les conflits/erreurs
                conflicts = response.get('conflicts', [])
                stats['errors'] = len(conflicts)

            # Pour les événements et tracker (structure différente)
            elif 'bundleReport' in result:
                bundle_report = result['bundleReport']
                type_report_map = bundle_report.get('typeReportMap', {})

                for type_name, type_report in type_report_map.items():
                    report_stats = type_report.get('stats', {})
                    stats['imported'] += report_stats.get('created', 0)
                    stats['updated'] += report_stats.get('updated', 0)
                    stats['ignored'] += report_stats.get('ignored', 0)
                    stats['deleted'] += report_stats.get('deleted', 0)

                    # Compter les erreurs dans les object reports
                    object_reports = type_report.get('objectReports', [])
                    for obj_report in object_reports:
                        error_reports = obj_report.get('errorReports', [])
                        stats['errors'] += len(error_reports)

            # Structure alternative
            elif 'importSummary' in result:
                summary = result['importSummary']
                stats['imported'] = summary.get('importCount', 0)
                stats['updated'] = summary.get('updateCount', 0)
                stats['ignored'] = summary.get('ignoreCount', 0)
                stats['deleted'] = summary.get('deleteCount', 0)
                stats['errors'] = len(summary.get('conflicts', []))

        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse du résultat d'import: {e}")

        return stats

    def validate_org_units(self, org_units: List[str]) -> List[str]:
        """
        Valide que les unités d'organisation existent sur l'instance source

        Args:
            org_units: Liste des UIDs d'unités d'organisation

        Returns:
            Liste des UIDs valides
        """
        try:
            if not org_units:
                return []

            # Récupérer les unités d'organisation existantes
            existing_orgunits = self.source_instance.get_metadata(
                'organisationUnits',
                fields='id',
                paging=False
            )

            existing_ids = {ou.get('id') for ou in existing_orgunits}
            valid_orgunits = [ou for ou in org_units if ou in existing_ids]

            if len(valid_orgunits) != len(org_units):
                invalid_orgunits = set(org_units) - set(valid_orgunits)
                self.logger.warning(f"Unités d'organisation invalides ignorées: {invalid_orgunits}")

            return valid_orgunits

        except Exception as e:
            self.logger.error(f"Erreur validation unités d'organisation: {e}")
            return org_units  # Retourner la liste originale en cas d'erreur

    def validate_periods(self, periods: List[str]) -> List[str]:
        """
        Valide le format des périodes

        Args:
            periods: Liste des périodes

        Returns:
            Liste des périodes valides
        """
        try:
            valid_periods = []

            for period in periods:
                # Validation basique du format des périodes DHIS2
                # Exemples: 2023, 202301, 2023W01, 2023Q1, etc.
                if isinstance(period, str) and len(period) >= 4:
                    valid_periods.append(period)
                else:
                    self.logger.warning(f"Format de période invalide ignoré: {period}")

            return valid_periods

        except Exception as e:
            self.logger.error(f"Erreur validation périodes: {e}")
            return periods  # Retourner la liste originale en cas d'erreur

    def chunk_data(self, data: List[Any], chunk_size: int = 1000) -> List[List[Any]]:
        """
        Divise les données en chunks pour traitement par lots

        Args:
            data: Données à diviser
            chunk_size: Taille des chunks

        Returns:
            Liste de chunks
        """
        chunks = []
        for i in range(0, len(data), chunk_size):
            chunks.append(data[i:i + chunk_size])
        return chunks

    def _format_sync_log(self, resource: str, source_count: int, stats: Dict[str, int]) -> str:
        """
        Formate un message de log détaillé pour une synchronisation de données

        Args:
            resource: Nom de la ressource (ex: 'dataValues', 'events', 'trackedEntityInstances')
            source_count: Nombre d'éléments récupérés de la source
            stats: Statistiques d'import (imported, updated, ignored, deleted, errors)

        Returns:
            Message de log formaté
        """
        created = stats.get('imported', 0)
        updated = stats.get('updated', 0)
        ignored = stats.get('ignored', 0)
        deleted = stats.get('deleted', 0)
        errors = stats.get('errors', 0)

        # Format: ✓ resource: Source=X | Created=Y, Updated=Z | Ignored=W | Deleted=D | Errors=E
        log_parts = [
            f"Source={source_count}",
            f"Created={created}, Updated={updated}",
            f"Ignored={ignored}",
        ]

        # Ajouter deleted si > 0 ou si c'est pertinent pour la ressource
        if deleted > 0:
            log_parts.append(f"Deleted={deleted}")

        # Ajouter errors
        log_parts.append(f"Errors={errors}")

        return f"✓ {resource}: {' | '.join(log_parts)}\n"