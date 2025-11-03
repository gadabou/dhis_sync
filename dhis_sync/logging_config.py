"""
Configuration du système de logging pour DHIS2 Sync

Ce fichier configure les loggers pour toute l'application,
avec une attention particulière pour la synchronisation automatique.
"""

import os
from pathlib import Path

# Répertoire de base
BASE_DIR = Path(__file__).resolve().parent.parent

# Créer le répertoire logs s'il n'existe pas
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Configuration des logs
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    # Formatters
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module}.{funcName}:{lineno} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {asctime} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'auto_sync': {
            'format': '[AUTO-SYNC] [{levelname}] {asctime} [{name}] - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },

    # Handlers
    'handlers': {
        # Console handler
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },

        # Fichier général
        'file_general': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'dhis2_sync.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },

        # Fichier pour les erreurs
        'file_errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },

        # Fichier spécifique pour auto-sync
        'file_auto_sync': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'auto_sync.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'auto_sync',
        },

        # Fichier pour les changements détectés
        'file_changes': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'changes_detected.log',
            'maxBytes': 5242880,  # 5MB
            'backupCount': 5,
            'formatter': 'auto_sync',
        },

        # Fichier pour les synchronisations
        'file_sync_jobs': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sync_jobs.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },

    # Loggers
    'loggers': {
        # Logger Django général
        'django': {
            'handlers': ['console', 'file_general'],
            'level': 'INFO',
            'propagate': False,
        },

        # Logger de l'application dhis_app
        'dhis_app': {
            'handlers': ['console', 'file_general', 'file_errors'],
            'level': 'INFO',
            'propagate': False,
        },

        # Logger pour la synchronisation automatique
        'dhis_app.services.auto_sync': {
            'handlers': ['console', 'file_auto_sync', 'file_errors'],
            'level': 'DEBUG',
            'propagate': False,
        },

        # Logger pour le détecteur de changements
        'dhis_app.services.auto_sync.change_detector': {
            'handlers': ['console', 'file_auto_sync', 'file_changes'],
            'level': 'DEBUG',
            'propagate': False,
        },

        # Logger pour le lifecycle manager
        'dhis_app.services.auto_sync.lifecycle_manager': {
            'handlers': ['console', 'file_auto_sync', 'file_sync_jobs'],
            'level': 'DEBUG',
            'propagate': False,
        },

        # Logger pour le scheduler
        'dhis_app.services.auto_sync.scheduler': {
            'handlers': ['console', 'file_auto_sync'],
            'level': 'INFO',
            'propagate': False,
        },

        # Logger pour les jobs de sync
        'dhis_app.services.sync_orchestrator': {
            'handlers': ['console', 'file_sync_jobs', 'file_errors'],
            'level': 'INFO',
            'propagate': False,
        },
    },

    # Logger par défaut
    'root': {
        'handlers': ['console', 'file_general'],
        'level': 'INFO',
    },
}
