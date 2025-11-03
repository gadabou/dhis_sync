"""
Scheduler pour la synchronisation automatique DHIS2

Ce service gère la planification et l'exécution périodique des synchronisations automatiques.
Il utilise un système de thread pour surveiller en continu les changements.
"""

import logging
import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone

from ...models import SyncConfiguration, AutoSyncSettings
from .change_detector import DHIS2ChangeDetector
from .lifecycle_manager import AutoSyncLifecycleManager

logger = logging.getLogger(__name__)


class AutoSyncScheduler:
    """
    Scheduler pour la synchronisation automatique

    Gère:
    - Le monitoring périodique des changements
    - Le déclenchement automatique des synchronisations
    - La gestion de multiples configurations simultanées
    """

    # Instance singleton du scheduler
    _instance: Optional['AutoSyncScheduler'] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Pattern Singleton pour avoir un seul scheduler actif"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialise le scheduler"""
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.running = False
            self.threads: Dict[int, threading.Thread] = {}
            self.stop_events: Dict[int, threading.Event] = {}
            self.logger = logger
            self.logger.info("AutoSyncScheduler initialisé")

    @classmethod
    def get_instance(cls) -> 'AutoSyncScheduler':
        """Retourne l'instance singleton du scheduler"""
        return cls()

    def start(self, sync_config_id: Optional[int] = None):
        """
        Démarre le scheduler pour une ou toutes les configurations

        Args:
            sync_config_id: ID de la configuration à démarrer (None = toutes les configs actives)
        """
        if sync_config_id:
            self._start_config(sync_config_id)
            print("scheduler start 1 ")
        else:
            self._start_all_active_configs()
            print("scheduler start All ")
        print("scheduler Pass ")

    def stop(self, sync_config_id: Optional[int] = None):
        """
        Arrête le scheduler pour une ou toutes les configurations

        Args:
            sync_config_id: ID de la configuration à arrêter (None = toutes)
        """
        if sync_config_id:
            self._stop_config(sync_config_id)
        else:
            self._stop_all_configs()

    def _start_config(self, sync_config_id: int):
        """Démarre le monitoring pour une configuration spécifique"""
        try:
            # Vérifier si déjà en cours
            if sync_config_id in self.threads and self.threads[sync_config_id].is_alive():
                self.logger.warning(f"Scheduler déjà actif pour la configuration {sync_config_id}")
                return

            # Charger la configuration
            try:
                sync_config = SyncConfiguration.objects.get(id=sync_config_id)
            except SyncConfiguration.DoesNotExist:
                self.logger.error(f"Configuration {sync_config_id} introuvable")
                return

            # Vérifier que la configuration est en mode automatique
            if sync_config.execution_mode != 'automatic':
                self.logger.warning(
                    f"Configuration {sync_config.name} n'est pas en mode automatique "
                    f"(mode actuel: {sync_config.execution_mode})"
                )
                return

            # Créer un événement d'arrêt
            stop_event = threading.Event()
            self.stop_events[sync_config_id] = stop_event

            # Créer et démarrer le thread
            thread = threading.Thread(
                target=self._monitor_loop,
                args=(sync_config, stop_event),
                name=f"AutoSync-{sync_config_id}",
                daemon=True
            )
            self.threads[sync_config_id] = thread
            thread.start()

            self.logger.info(f"Scheduler démarré pour {sync_config.name} (ID: {sync_config_id})")

        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du scheduler pour {sync_config_id}: {e}", exc_info=True)

    def _stop_config(self, sync_config_id: int):
        """Arrête le monitoring pour une configuration spécifique"""
        try:
            if sync_config_id in self.stop_events:
                self.stop_events[sync_config_id].set()

            if sync_config_id in self.threads:
                thread = self.threads[sync_config_id]
                thread.join(timeout=10)  # Attendre max 10 secondes

                del self.threads[sync_config_id]
                del self.stop_events[sync_config_id]

                self.logger.info(f"Scheduler arrêté pour la configuration {sync_config_id}")

        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt du scheduler pour {sync_config_id}: {e}")

    def _start_all_active_configs(self):
        """Démarre le monitoring pour toutes les configurations actives en mode automatique"""
        try:
            active_configs = SyncConfiguration.objects.filter(execution_mode='automatic', is_active=True)

            for config in active_configs:
                try:
                    auto_sync_settings = config.auto_sync_settings
                    if auto_sync_settings.is_enabled:
                        self._start_config(config.id)
                except AutoSyncSettings.DoesNotExist:
                    self.logger.warning(f"Pas de paramètres auto-sync pour {config.name}")

            self.logger.info(f"{len(active_configs)} configurations démarrées")

        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage de toutes les configurations: {e}")

    def _stop_all_configs(self):
        """Arrête le monitoring pour toutes les configurations"""
        config_ids = list(self.threads.keys())
        for config_id in config_ids:
            self._stop_config(config_id)

        self.logger.info("Tous les schedulers arrêtés")

    def _monitor_loop(self, sync_config: SyncConfiguration, stop_event: threading.Event):
        """
        Boucle de monitoring pour une configuration

        Args:
            sync_config: Configuration à surveiller
            stop_event: Événement pour arrêter la boucle
        """
        self.logger.info(f"Démarrage de la boucle de monitoring pour {sync_config.name}")

        try:
            # Récupérer les paramètres
            auto_sync_settings = sync_config.auto_sync_settings
            check_interval = auto_sync_settings.check_interval

            # Créer les services
            change_detector = DHIS2ChangeDetector(
                source_instance=sync_config.source_instance,
                auto_sync_settings=auto_sync_settings
            )
            lifecycle_manager = AutoSyncLifecycleManager(sync_config)

            # Premier lancement: attendre un délai avant de démarrer
            if auto_sync_settings.delay_before_sync > 0:
                self.logger.info(
                    f"Délai initial de {auto_sync_settings.delay_before_sync}s "
                    f"avant la première synchronisation"
                )
                if stop_event.wait(auto_sync_settings.delay_before_sync):
                    return  # Arrêt demandé pendant le délai

            # Boucle principale
            while not stop_event.is_set():
                try:
                    # Vérifier si on peut synchroniser
                    can_sync = lifecycle_manager.can_sync_now()

                    if can_sync['can_sync']:
                        # Détecter les changements
                        self.logger.debug(f"Détection des changements pour {sync_config.name}")
                        changes = change_detector.detect_changes()

                        # S'il y a des changements, déclencher la synchronisation
                        if changes['has_changes']:
                            self.logger.info(
                                f"Changements détectés pour {sync_config.name}: "
                                f"Métadonnées={changes['metadata_changes']}, "
                                f"Données={changes['data_changes']}"
                            )

                            # Attendre le délai configuré avant sync si immediate_sync=False
                            if not auto_sync_settings.immediate_sync and auto_sync_settings.delay_before_sync > 0:
                                self.logger.info(f"Attente de {auto_sync_settings.delay_before_sync}s avant sync")
                                if stop_event.wait(auto_sync_settings.delay_before_sync):
                                    break

                            # Déclencher la synchronisation
                            result = lifecycle_manager.trigger_sync(change_details=changes)

                            if result['success']:
                                # Marquer toutes les ressources comme vérifiées
                                change_detector.mark_all_as_checked()
                                self.logger.info(f"Synchronisation réussie pour {sync_config.name}")
                            else:
                                self.logger.warning(
                                    f"Synchronisation échouée pour {sync_config.name}: "
                                    f"{result.get('message')}"
                                )
                        else:
                            self.logger.debug(f"Aucun changement détecté pour {sync_config.name}")
                    else:
                        self.logger.debug(
                            f"Synchronisation non disponible pour {sync_config.name}: "
                            f"{can_sync['reason']}"
                        )

                except Exception as e:
                    self.logger.error(
                        f"Erreur dans la boucle de monitoring pour {sync_config.name}: {e}",
                        exc_info=True
                    )

                # Attendre l'intervalle de vérification
                if stop_event.wait(check_interval):
                    break  # Arrêt demandé

        except Exception as e:
            self.logger.error(
                f"Erreur fatale dans la boucle de monitoring pour {sync_config.name}: {e}",
                exc_info=True
            )
        finally:
            self.logger.info(f"Fin de la boucle de monitoring pour {sync_config.name}")

    def get_status(self, sync_config_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retourne le statut du scheduler

        Args:
            sync_config_id: ID de la configuration (None = toutes)

        Returns:
            Statut du scheduler
        """
        if sync_config_id:
            is_running = (
                sync_config_id in self.threads and
                self.threads[sync_config_id].is_alive()
            )
            return {
                'config_id': sync_config_id,
                'is_running': is_running,
                'thread_name': self.threads.get(sync_config_id, {}).name if is_running else None
            }
        else:
            active_configs = []
            for config_id, thread in self.threads.items():
                if thread.is_alive():
                    active_configs.append({
                        'config_id': config_id,
                        'thread_name': thread.name,
                        'is_alive': True
                    })

            return {
                'total_active': len(active_configs),
                'active_configs': active_configs
            }

    def restart(self, sync_config_id: int):
        """
        Redémarre le scheduler pour une configuration

        Args:
            sync_config_id: ID de la configuration à redémarrer
        """
        self.logger.info(f"Redémarrage du scheduler pour la configuration {sync_config_id}")
        self._stop_config(sync_config_id)
        time.sleep(1)  # Petit délai pour s'assurer que le thread est bien arrêté
        self._start_config(sync_config_id)


# Fonction helper pour démarrer/arrêter facilement
def start_auto_sync(sync_config_id: Optional[int] = None):
    """
    Démarre la synchronisation automatique

    Args:
        sync_config_id: ID de la configuration (None = toutes)
    """
    scheduler = AutoSyncScheduler.get_instance()
    scheduler.start(sync_config_id)


def stop_auto_sync(sync_config_id: Optional[int] = None):
    """
    Arrête la synchronisation automatique

    Args:
        sync_config_id: ID de la configuration (None = toutes)
    """
    scheduler = AutoSyncScheduler.get_instance()
    scheduler.stop(sync_config_id)


def restart_auto_sync(sync_config_id: int):
    """
    Redémarre la synchronisation automatique

    Args:
        sync_config_id: ID de la configuration
    """
    scheduler = AutoSyncScheduler.get_instance()
    scheduler.restart(sync_config_id)


def get_auto_sync_status(sync_config_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Retourne le statut de la synchronisation automatique

    Args:
        sync_config_id: ID de la configuration (None = toutes)

    Returns:
        Statut du scheduler
    """
    scheduler = AutoSyncScheduler.get_instance()
    return scheduler.get_status(sync_config_id)
