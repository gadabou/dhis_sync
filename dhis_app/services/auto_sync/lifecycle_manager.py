"""
Gestionnaire du cycle de vie de la synchronisation automatique

Ce service gère:
- Le premier lancement de la synchronisation (métadonnées puis données)
- Les synchronisations suivantes (uniquement les changements)
- La gestion des erreurs et des retries
- La limitation du nombre de synchronisations
"""

import logging
from typing import Dict, Any, Optional
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache

from ...models import SyncConfiguration, SyncJob, AutoSyncSettings
from ..sync_orchestrator import SyncOrchestrator

logger = logging.getLogger(__name__)


class AutoSyncLifecycleManager:
    """
    Gestionnaire du cycle de vie des synchronisations automatiques

    Responsabilités:
    - Déterminer si c'est le premier lancement ou une synchronisation incrémentale
    - Orchestrer l'ordre: métadonnées → données
    - Gérer les limites de synchronisation (max par heure)
    - Gérer les cooldowns après erreur
    """

    # Clés de cache
    CACHE_PREFIX = "auto_sync_lifecycle"
    CACHE_TIMEOUT = 3600 * 24  # 24 heures

    # États du cycle de vie
    STATE_INITIAL = 'initial'  # Premier lancement
    STATE_METADATA_DONE = 'metadata_done'  # Métadonnées synchronisées
    STATE_RUNNING = 'running'  # Synchronisation active
    STATE_COOLDOWN = 'cooldown'  # En attente après erreur
    STATE_THROTTLED = 'throttled'  # Limite de synchronisations atteinte

    def __init__(self, sync_config: SyncConfiguration):
        """
        Initialise le gestionnaire de cycle de vie

        Args:
            sync_config: Configuration de synchronisation
        """
        self.sync_config = sync_config
        self.auto_sync_settings = self._get_or_create_auto_sync_settings()
        self.logger = logger

    def _get_or_create_auto_sync_settings(self) -> AutoSyncSettings:
        """Récupère ou crée les paramètres de synchronisation automatique"""
        try:
            return self.sync_config.auto_sync_settings
        except AutoSyncSettings.DoesNotExist:
            # Créer avec des valeurs par défaut
            return AutoSyncSettings.objects.create(
                sync_config=self.sync_config,
                is_enabled=True,
                check_interval=300,
                monitor_metadata=True,
                monitor_data_values=True
            )

    def can_sync_now(self) -> Dict[str, Any]:
        """
        Vérifie si une synchronisation peut être lancée maintenant

        Returns:
            {
                'can_sync': bool,
                'reason': str,
                'state': str,
                'retry_after': int (secondes)
            }
        """
        # Vérifier si la synchronisation automatique est activée
        if not self.auto_sync_settings.is_enabled:
            return {
                'can_sync': False,
                'reason': 'Synchronisation automatique désactivée',
                'state': 'disabled'
            }

        # Vérifier s'il y a déjà une synchronisation en cours
        if self._is_sync_running():
            return {
                'can_sync': False,
                'reason': 'Une synchronisation est déjà en cours',
                'state': self.STATE_RUNNING
            }

        # Vérifier le cooldown après erreur
        cooldown_check = self._check_cooldown()
        if not cooldown_check['can_sync']:
            return cooldown_check

        # Vérifier le throttling (limite de syncs par heure)
        throttle_check = self._check_throttle()
        if not throttle_check['can_sync']:
            return throttle_check

        return {
            'can_sync': True,
            'reason': 'Prêt pour la synchronisation',
            'state': self._get_current_state()
        }

    def trigger_sync(self, change_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Déclenche une synchronisation automatique

        Args:
            change_details: Détails des changements détectés

        Returns:
            Résultat de la synchronisation
        """
        # Vérifier si on peut synchroniser
        can_sync_result = self.can_sync_now()
        if not can_sync_result['can_sync']:
            return {
                'success': False,
                'message': can_sync_result['reason'],
                'state': can_sync_result.get('state')
            }

        try:
            # Déterminer le type de synchronisation à effectuer
            current_state = self._get_current_state()

            if current_state == self.STATE_INITIAL:
                # Premier lancement: métadonnées d'abord
                return self._execute_initial_sync()
            else:
                # Synchronisation incrémentale basée sur les changements
                return self._execute_incremental_sync(change_details)

        except Exception as e:
            self.logger.error(f"Erreur lors du déclenchement de la synchronisation: {e}", exc_info=True)
            self._enter_cooldown()
            return {
                'success': False,
                'message': f"Erreur: {str(e)}",
                'state': self.STATE_COOLDOWN
            }

    def _execute_initial_sync(self) -> Dict[str, Any]:
        """
        Exécute la synchronisation initiale (premier lancement)

        Ordre: métadonnées → données
        """
        self.logger.info(f"Démarrage de la synchronisation initiale pour {self.sync_config.name}")

        try:
            # Marquer comme en cours
            self._set_sync_running(True)
            self._increment_sync_counter()

            orchestrator = SyncOrchestrator(self.sync_config)

            # Étape 1: Synchroniser les métadonnées
            self.logger.info("Étape 1/2: Synchronisation des métadonnées")
            metadata_job = orchestrator.execute_metadata_sync(
                sync_config=self.sync_config
            )

            # Vérifier le succès de la synchronisation des métadonnées
            if metadata_job.status not in ['completed', 'completed_with_warnings']:
                self._set_sync_running(False)
                self._enter_cooldown()
                return {
                    'success': False,
                    'message': 'Échec de la synchronisation des métadonnées',
                    'job': metadata_job,
                    'state': self.STATE_COOLDOWN
                }

            # Marquer les métadonnées comme synchronisées
            self._set_state(self.STATE_METADATA_DONE)

            # Étape 2: Synchroniser les données
            self.logger.info("Étape 2/2: Synchronisation des données")

            # Déterminer les types de données à synchroniser
            data_sync_types = self._get_data_sync_types()

            if data_sync_types:
                data_job = orchestrator.execute_data_sync(
                    sync_config=self.sync_config,
                    sync_types=data_sync_types
                )

                success = data_job.status in ['completed', 'completed_with_warnings']
            else:
                self.logger.info("Aucune donnée à synchroniser selon la configuration")
                data_job = None
                success = True

            # Finaliser
            self._set_sync_running(False)

            if success:
                self.logger.info("Synchronisation initiale terminée avec succès")
                return {
                    'success': True,
                    'message': 'Synchronisation initiale réussie',
                    'metadata_job': metadata_job,
                    'data_job': data_job,
                    'state': self.STATE_METADATA_DONE
                }
            else:
                self._enter_cooldown()
                return {
                    'success': False,
                    'message': 'Échec de la synchronisation des données',
                    'metadata_job': metadata_job,
                    'data_job': data_job,
                    'state': self.STATE_COOLDOWN
                }

        except Exception as e:
            self._set_sync_running(False)
            self._enter_cooldown()
            self.logger.error(f"Erreur lors de la synchronisation initiale: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"Erreur: {str(e)}",
                'state': self.STATE_COOLDOWN
            }

    def _execute_incremental_sync(self, change_details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Exécute une synchronisation incrémentale basée sur les changements détectés

        Args:
            change_details: Détails des changements (metadata_changes, data_changes, etc.)
        """
        self.logger.info(f"Démarrage de la synchronisation incrémentale pour {self.sync_config.name}")

        try:
            self._set_sync_running(True)
            self._increment_sync_counter()

            orchestrator = SyncOrchestrator(self.sync_config)
            jobs = []

            # Synchroniser les métadonnées si nécessaire
            if change_details and change_details.get('metadata_changes'):
                self.logger.info("Synchronisation des métadonnées modifiées")
                metadata_job = orchestrator.execute_metadata_sync(
                    sync_config=self.sync_config
                )
                jobs.append(('metadata', metadata_job))

            # Synchroniser les données si nécessaire
            if change_details and change_details.get('data_changes'):
                self.logger.info("Synchronisation des données modifiées")

                # Déterminer quels types de données ont changé
                data_details = change_details.get('changes_details', {})
                sync_types = []

                if data_details.get('aggregate', {}).get('has_changes'):
                    sync_types.append('aggregate')
                if data_details.get('events', {}).get('has_changes'):
                    sync_types.append('events')
                if data_details.get('tracker', {}).get('has_changes'):
                    sync_types.append('tracker')

                if sync_types:
                    data_job = orchestrator.execute_data_sync(
                        sync_config=self.sync_config,
                        sync_types=sync_types
                    )
                    jobs.append(('data', data_job))

            # Si aucun changement spécifique détecté, faire une synchronisation complète
            if not jobs:
                self.logger.info("Aucun changement spécifique détecté, synchronisation complète")
                full_job = orchestrator.execute_full_sync(
                    sync_config=self.sync_config
                )
                jobs.append(('complete', full_job))

            # Analyser les résultats
            self._set_sync_running(False)

            all_success = all(
                job.status in ['completed', 'completed_with_warnings']
                for _, job in jobs
            )

            if all_success:
                self.logger.info("Synchronisation incrémentale réussie")
                return {
                    'success': True,
                    'message': 'Synchronisation incrémentale réussie',
                    'jobs': jobs,
                    'state': self.STATE_METADATA_DONE
                }
            else:
                self._enter_cooldown()
                return {
                    'success': False,
                    'message': 'Échec de la synchronisation incrémentale',
                    'jobs': jobs,
                    'state': self.STATE_COOLDOWN
                }

        except Exception as e:
            self._set_sync_running(False)
            self._enter_cooldown()
            self.logger.error(f"Erreur lors de la synchronisation incrémentale: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"Erreur: {str(e)}",
                'state': self.STATE_COOLDOWN
            }

    def _get_data_sync_types(self) -> list:
        """Retourne les types de données à synchroniser selon la configuration"""
        sync_type = self.sync_config.sync_type

        if sync_type == 'complete':
            return ['tracker', 'events', 'aggregate']
        elif sync_type == 'all_data':
            return ['tracker', 'events', 'aggregate']
        elif sync_type == 'both':
            return [self.sync_config.data_type or 'aggregate']
        elif sync_type == 'data':
            return [self.sync_config.data_type or 'aggregate']
        elif sync_type in ['tracker', 'events']:
            return [sync_type]
        else:
            return []

    def _is_sync_running(self) -> bool:
        """Vérifie si une synchronisation est en cours"""
        # Vérifier dans le cache
        cache_key = f"{self.CACHE_PREFIX}:running:{self.sync_config.id}"
        is_running = cache.get(cache_key, False)

        if is_running:
            return True

        # Vérifier s'il y a des jobs en cours dans la base
        active_jobs = SyncJob.objects.filter(
            sync_config=self.sync_config,
            status__in=['pending', 'running']
        ).exists()

        return active_jobs

    def _set_sync_running(self, running: bool):
        """Marque la synchronisation comme en cours ou terminée"""
        cache_key = f"{self.CACHE_PREFIX}:running:{self.sync_config.id}"
        if running:
            cache.set(cache_key, True, timeout=3600)  # 1 heure max
        else:
            cache.delete(cache_key)

    def _check_cooldown(self) -> Dict[str, Any]:
        """Vérifie si on est en période de cooldown après une erreur"""
        cache_key = f"{self.CACHE_PREFIX}:cooldown:{self.sync_config.id}"
        cooldown_until = cache.get(cache_key)

        if cooldown_until:
            cooldown_datetime = timezone.datetime.fromisoformat(cooldown_until)
            now = timezone.now()

            if now < cooldown_datetime:
                remaining = int((cooldown_datetime - now).total_seconds())
                return {
                    'can_sync': False,
                    'reason': f'En cooldown après erreur (reste {remaining}s)',
                    'state': self.STATE_COOLDOWN,
                    'retry_after': remaining
                }

        return {'can_sync': True}

    def _enter_cooldown(self):
        """Active le cooldown après une erreur"""
        cache_key = f"{self.CACHE_PREFIX}:cooldown:{self.sync_config.id}"
        cooldown_until = timezone.now() + timedelta(
            seconds=self.auto_sync_settings.cooldown_after_error
        )
        cache.set(cache_key, cooldown_until.isoformat(), timeout=self.auto_sync_settings.cooldown_after_error)
        self.logger.info(f"Cooldown activé jusqu'à {cooldown_until}")

    def _check_throttle(self) -> Dict[str, Any]:
        """Vérifie le throttling (limite de syncs par heure)"""
        cache_key = f"{self.CACHE_PREFIX}:throttle:{self.sync_config.id}"
        sync_count = cache.get(cache_key, 0)

        max_per_hour = self.auto_sync_settings.max_sync_per_hour

        if sync_count >= max_per_hour:
            return {
                'can_sync': False,
                'reason': f'Limite de {max_per_hour} synchronisations par heure atteinte',
                'state': self.STATE_THROTTLED,
                'retry_after': 3600  # Réessayer dans 1 heure
            }

        return {'can_sync': True}

    def _increment_sync_counter(self):
        """Incrémente le compteur de synchronisations par heure"""
        cache_key = f"{self.CACHE_PREFIX}:throttle:{self.sync_config.id}"
        current_count = cache.get(cache_key, 0)
        cache.set(cache_key, current_count + 1, timeout=3600)  # 1 heure

    def _get_current_state(self) -> str:
        """Retourne l'état actuel du cycle de vie"""
        cache_key = f"{self.CACHE_PREFIX}:state:{self.sync_config.id}"
        state = cache.get(cache_key, self.STATE_INITIAL)
        return state

    def _set_state(self, state: str):
        """Définit l'état actuel du cycle de vie"""
        cache_key = f"{self.CACHE_PREFIX}:state:{self.sync_config.id}"
        cache.set(cache_key, state, timeout=self.CACHE_TIMEOUT)

    def reset_state(self):
        """Réinitialise l'état (pour forcer une synchronisation complète)"""
        self._set_state(self.STATE_INITIAL)
        self.logger.info(f"État réinitialisé pour {self.sync_config.name}")
