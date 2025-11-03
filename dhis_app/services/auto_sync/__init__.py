"""
Services de synchronisation automatique DHIS2

Ce package contient tous les services nécessaires pour la synchronisation automatique:
- change_detector: Détection des changements sur l'instance source
- lifecycle_manager: Gestion du cycle de vie des synchronisations automatiques
- scheduler: Planification et orchestration des synchronisations
- tasks: Tâches asynchrones pour l'exécution en arrière-plan
"""

from .change_detector import DHIS2ChangeDetector
from .lifecycle_manager import AutoSyncLifecycleManager
from .scheduler import AutoSyncScheduler

__all__ = [
    'DHIS2ChangeDetector',
    'AutoSyncLifecycleManager',
    'AutoSyncScheduler',
]
