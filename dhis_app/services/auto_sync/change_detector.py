"""
Service de détection des changements DHIS2

Ce service surveille l'instance source pour détecter les modifications
de métadonnées et de données, puis déclenche la synchronisation automatique.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


class DHIS2ChangeDetector:
    """
    Détecteur de changements pour DHIS2

    Utilise l'API système de DHIS2 pour détecter les modifications:
    - /api/system/info pour les métadonnées
    - /api/dataValueSets avec lastUpdated pour les données agrégées
    - /api/events avec lastUpdated pour les événements
    - /api/trackedEntityInstances avec lastUpdated pour le tracker
    """

    # Clés de cache pour stocker les dernières timestamps
    CACHE_PREFIX = "dhis2_change_detector"
    CACHE_TIMEOUT = 3600 * 24  # 24 heures

    def __init__(self, source_instance, auto_sync_settings):
        """
        Initialise le détecteur de changements

        Args:
            source_instance: Instance DHIS2 source à surveiller
            auto_sync_settings: Configuration de synchronisation automatique
        """
        self.source_instance = source_instance
        self.auto_sync_settings = auto_sync_settings
        self.api = source_instance.get_api_client()
        self.logger = logger

    def detect_changes(self) -> Dict[str, Any]:
        """
        Détecte tous les types de changements configurés

        Returns:
            Dictionnaire avec les changements détectés:
            {
                'has_changes': bool,
                'metadata_changes': bool,
                'data_changes': bool,
                'changes_details': {
                    'metadata': [...],
                    'aggregate': {...},
                    'events': {...},
                    'tracker': {...}
                }
            }
        """
        results = {
            'has_changes': False,
            'metadata_changes': False,
            'data_changes': False,
            'changes_details': {}
        }

        try:
            # Détecter les changements de métadonnées
            if self.auto_sync_settings.monitor_metadata:
                metadata_changes = self._detect_metadata_changes()
                results['metadata_changes'] = metadata_changes['has_changes']
                results['changes_details']['metadata'] = metadata_changes['changed_resources']

            # Détecter les changements de données
            if self.auto_sync_settings.monitor_data_values:
                data_changes = self._detect_data_changes()
                results['data_changes'] = data_changes['has_changes']
                results['changes_details'].update(data_changes['details'])

            results['has_changes'] = results['metadata_changes'] or results['data_changes']

            self.logger.info(
                f"Détection de changements pour {self.source_instance.name}: "
                f"Métadonnées={results['metadata_changes']}, "
                f"Données={results['data_changes']}"
            )

            return results

        except Exception as e:
            self.logger.error(f"Erreur lors de la détection de changements: {e}", exc_info=True)
            return results

    def _detect_metadata_changes(self) -> Dict[str, Any]:
        """
        Détecte les changements de métadonnées

        Utilise l'endpoint /api/metadata pour obtenir les lastUpdated des ressources
        """
        result = {
            'has_changes': False,
            'changed_resources': []
        }

        try:
            # Liste des ressources à surveiller
            resources_to_monitor = self.auto_sync_settings.metadata_resources or [
                'organisationUnits',
                'dataElements',
                'indicators',
                'programs',
                'dataSets',
                'categoryOptions',
                'categories',
                'categoryCombos',
            ]

            # Exclure certaines ressources si configuré
            exclude_resources = self.auto_sync_settings.exclude_resources or []
            resources_to_monitor = [
                r for r in resources_to_monitor
                if r not in exclude_resources
            ]

            for resource in resources_to_monitor:
                try:
                    # Obtenir la dernière timestamp connue
                    last_check = self._get_last_check_timestamp('metadata', resource)

                    # Vérifier s'il y a des modifications depuis last_check
                    has_changes = self._check_resource_changes(resource, last_check)

                    if has_changes:
                        result['has_changes'] = True
                        result['changed_resources'].append(resource)
                        self.logger.info(f"Changements détectés pour {resource}")

                except Exception as e:
                    self.logger.warning(f"Erreur lors de la vérification de {resource}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Erreur lors de la détection des métadonnées: {e}")

        return result

    def _detect_data_changes(self) -> Dict[str, Any]:
        """
        Détecte les changements de données (aggregate, events, tracker)
        """
        result = {
            'has_changes': False,
            'details': {
                'aggregate': {'has_changes': False, 'count': 0},
                'events': {'has_changes': False, 'count': 0},
                'tracker': {'has_changes': False, 'count': 0}
            }
        }

        try:
            # Configuration de sync pour déterminer les types de données à surveiller
            sync_config = self.auto_sync_settings.sync_config

            # Vérifier les données agrégées
            if sync_config.sync_type in ['data', 'both', 'all_data', 'complete']:
                aggregate_changes = self._check_aggregate_changes()
                result['details']['aggregate'] = aggregate_changes
                if aggregate_changes['has_changes']:
                    result['has_changes'] = True

            # Vérifier les événements
            if sync_config.sync_type in ['events', 'all_data', 'complete']:
                events_changes = self._check_events_changes()
                result['details']['events'] = events_changes
                if events_changes['has_changes']:
                    result['has_changes'] = True

            # Vérifier le tracker
            if sync_config.sync_type in ['tracker', 'all_data', 'complete']:
                tracker_changes = self._check_tracker_changes()
                result['details']['tracker'] = tracker_changes
                if tracker_changes['has_changes']:
                    result['has_changes'] = True

        except Exception as e:
            self.logger.error(f"Erreur lors de la détection des données: {e}")

        return result

    def _check_resource_changes(self, resource: str, last_check: datetime) -> bool:
        """
        Vérifie si une ressource a été modifiée depuis last_check

        Args:
            resource: Type de ressource (ex: 'organisationUnits')
            last_check: Dernière vérification

        Returns:
            True si des changements sont détectés
        """
        try:
            # Utiliser un filtre lastUpdated si supporté
            params = {
                'fields': 'id,lastUpdated',
                'paging': 'true',
                'pageSize': 1,  # On veut juste savoir s'il y a des changements
            }

            # Ajouter filtre temporel si last_check existe
            if last_check:
                # Format: YYYY-MM-DDTHH:mm:ss
                last_check_str = last_check.strftime('%Y-%m-%dT%H:%M:%S')
                params['filter'] = f'lastUpdated:gt:{last_check_str}'

            response = self.api.get(resource, params=params)

            if response.status_code == 200:
                data = response.json()

                # Vérifier s'il y a des résultats
                if isinstance(data, dict):
                    items = data.get(resource, [])
                    pager = data.get('pager', {})
                    total = pager.get('total', len(items))

                    return total > 0

            return False

        except Exception as e:
            self.logger.warning(f"Erreur lors de la vérification de {resource}: {e}")
            return False

    def _check_aggregate_changes(self) -> Dict[str, Any]:
        """
        Vérifie les changements dans les données agrégées
        """
        result = {'has_changes': False, 'count': 0}

        try:
            last_check = self._get_last_check_timestamp('data', 'aggregate')

            # Vérifier via l'audit ou dataValueAudit si disponible
            # Sinon, utiliser une approche basée sur les jobs récents
            params = {
                'paging': 'true',
                'pageSize': 1
            }

            if last_check:
                # Chercher des valeurs modifiées depuis last_check
                last_check_str = last_check.strftime('%Y-%m-%d')
                # Note: DHIS2 ne supporte pas toujours lastUpdated sur dataValues
                # On peut utiliser l'API d'audit si disponible
                try:
                    response = self.api.get('dataValueAudits', params={
                        'startDate': last_check_str,
                        'paging': 'true',
                        'pageSize': 1
                    })

                    if response.status_code == 200:
                        data = response.json()
                        total = data.get('pager', {}).get('total', 0)
                        result['has_changes'] = total > 0
                        result['count'] = total
                except:
                    # Fallback: considérer qu'il y a toujours des changements
                    # pour ne pas manquer de synchronisations
                    result['has_changes'] = True

        except Exception as e:
            self.logger.warning(f"Erreur vérification données agrégées: {e}")

        return result

    def _check_events_changes(self) -> Dict[str, Any]:
        """
        Vérifie les changements dans les événements
        """
        result = {'has_changes': False, 'count': 0}

        try:
            last_check = self._get_last_check_timestamp('data', 'events')

            params = {
                'skipPaging': 'false',
                'pageSize': 1,
                'totalPages': 'true'
            }

            if last_check:
                last_check_str = last_check.strftime('%Y-%m-%d')
                params['lastUpdatedStartDate'] = last_check_str

            response = self.api.get('events', params=params)

            if response.status_code == 200:
                data = response.json()
                pager = data.get('pager', {})
                total = pager.get('total', 0)

                result['has_changes'] = total > 0
                result['count'] = total

        except Exception as e:
            self.logger.warning(f"Erreur vérification événements: {e}")

        return result

    def _check_tracker_changes(self) -> Dict[str, Any]:
        """
        Vérifie les changements dans le tracker (TEI)
        """
        result = {'has_changes': False, 'count': 0}

        try:
            last_check = self._get_last_check_timestamp('data', 'tracker')

            params = {
                'skipPaging': 'false',
                'pageSize': 1,
                'totalPages': 'true'
            }

            if last_check:
                last_check_str = last_check.strftime('%Y-%m-%d')
                params['lastUpdatedStartDate'] = last_check_str

            response = self.api.get('trackedEntityInstances', params=params)

            if response.status_code == 200:
                data = response.json()
                # TEI peut retourner une liste directe ou avec pager
                if isinstance(data, dict):
                    pager = data.get('pager', {})
                    total = pager.get('total', len(data.get('trackedEntityInstances', [])))
                else:
                    total = len(data) if isinstance(data, list) else 0

                result['has_changes'] = total > 0
                result['count'] = total

        except Exception as e:
            self.logger.warning(f"Erreur vérification tracker: {e}")

        return result

    def _get_last_check_timestamp(self, category: str, resource: str) -> Optional[datetime]:
        """
        Récupère la dernière timestamp de vérification depuis le cache

        Args:
            category: 'metadata' ou 'data'
            resource: Nom de la ressource

        Returns:
            Datetime de la dernière vérification ou None
        """
        cache_key = f"{self.CACHE_PREFIX}:{self.source_instance.id}:{category}:{resource}"
        timestamp = cache.get(cache_key)

        if timestamp:
            return datetime.fromisoformat(timestamp)
        return None

    def update_last_check_timestamp(self, category: str, resource: str, timestamp: Optional[datetime] = None):
        """
        Met à jour la dernière timestamp de vérification dans le cache

        Args:
            category: 'metadata' ou 'data'
            resource: Nom de la ressource
            timestamp: Timestamp à enregistrer (par défaut: maintenant)
        """
        if timestamp is None:
            timestamp = timezone.now()

        cache_key = f"{self.CACHE_PREFIX}:{self.source_instance.id}:{category}:{resource}"
        cache.set(cache_key, timestamp.isoformat(), self.CACHE_TIMEOUT)

    def mark_all_as_checked(self):
        """
        Marque toutes les ressources comme vérifiées (utilisé après une sync réussie)
        """
        now = timezone.now()

        # Marquer les métadonnées
        if self.auto_sync_settings.monitor_metadata:
            resources = self.auto_sync_settings.metadata_resources or []
            for resource in resources:
                self.update_last_check_timestamp('metadata', resource, now)

        # Marquer les données
        if self.auto_sync_settings.monitor_data_values:
            for data_type in ['aggregate', 'events', 'tracker']:
                self.update_last_check_timestamp('data', data_type, now)

        self.logger.info(f"Toutes les ressources marquées comme vérifiées à {now}")
