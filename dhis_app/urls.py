from django.urls import path
from .views.dashboard import DashboardView
from .views.dhis2_instance import (
    DHIS2InstanceListView,
    DHIS2InstanceDetailView,
    DHIS2InstanceCreateView,
    DHIS2InstanceUpdateView,
    DHIS2InstanceDeleteView,
    DHIS2InstanceToggleStatusView,
    DHIS2InstanceTestConnectionView,
    DHIS2InstanceTestConnectionPageView,
    DHIS2InstanceMetadataView,
    DHIS2InstanceBulkStatusCheckView,
)
from .views.configurations import (
    SyncConfigurationListView,
    SyncConfigurationDetailView,
    SyncConfigurationCreateView,
    SyncConfigurationUpdateView,
    ToggleConfigurationStatusView,
    TestConfigurationCompatibilityView,
    CloneConfigurationView,
)
from .views.synchronisations import (
    LaunchSynchronizationView,
    LaunchMetadataSyncView,
    LaunchDataSyncView,
    GetSyncParametersView,
)
from .views.sync_jobs import (
    SyncJobDetailView,
)
from .views import auto_sync, logs

urlpatterns = [
    # === TABLEAU DE BORD ===
    path('', DashboardView.as_view(), name='dashboard'),
    # === INSTANCES DHIS2 ===
    # Liste des instances DHIS2
    path('instances/', DHIS2InstanceListView.as_view(), name='dhis2_instance_list'),

    # Créer une nouvelle instance
    path('instances/create/', DHIS2InstanceCreateView.as_view(), name='dhis2_instance_create'),

    # Détail d'une instance
    path('instances/<int:instance_id>/', DHIS2InstanceDetailView.as_view(), name='dhis2_instance_detail'),

    # Modifier une instance
    path('instances/<int:instance_id>/edit/', DHIS2InstanceUpdateView.as_view(), name='dhis2_instance_edit'),

    # Supprimer une instance
    path('instances/<int:instance_id>/delete/', DHIS2InstanceDeleteView.as_view(), name='dhis2_instance_delete'),

    # Activer/Désactiver une instance
    path('instances/<int:instance_id>/toggle-status/', DHIS2InstanceToggleStatusView.as_view(), name='dhis2_instance_toggle_status'),

    # Test de connexion (API JSON)
    path('instances/<int:instance_id>/test-connection/', DHIS2InstanceTestConnectionView.as_view(), name='dhis2_instance_test_connection'),

    # Page de test de connexion
    path('instances/<int:instance_id>/test-connection-page/', DHIS2InstanceTestConnectionPageView.as_view(), name='dhis2_instance_test_connection_page'),

    # Métadonnées d'une instance
    path('instances/<int:instance_id>/metadata/', DHIS2InstanceMetadataView.as_view(), name='dhis2_instance_metadata'),

    # Vérification bulk du statut des instances (API JSON)
    path('instances/bulk-status-check/', DHIS2InstanceBulkStatusCheckView.as_view(), name='dhis2_instance_bulk_status_check'),

    # === CONFIGURATIONS DE SYNCHRONISATION ===
    # Liste des configurations
    path('configurations/', SyncConfigurationListView.as_view(), name='sync_config_list'),

    # Créer une nouvelle configuration
    path('configurations/create/', SyncConfigurationCreateView.as_view(), name='sync_config_create'),

    # Détail d'une configuration
    path('configurations/<int:config_id>/', SyncConfigurationDetailView.as_view(), name='sync_config_detail'),

    # Modifier une configuration
    path('configurations/<int:config_id>/edit/', SyncConfigurationUpdateView.as_view(), name='sync_config_update'),

    # Activer/Désactiver une configuration
    path('configurations/<int:config_id>/toggle-status/', ToggleConfigurationStatusView.as_view(), name='sync_config_toggle_status'),

    # Test de compatibilité
    path('configurations/<int:config_id>/test-compatibility/', TestConfigurationCompatibilityView.as_view(), name='sync_config_test_compatibility'),

    # Cloner une configuration
    path('configurations/<int:config_id>/clone/', CloneConfigurationView.as_view(), name='sync_config_clone'),

    # === SYNCHRONISATION ===
    # Lancer une synchronisation complète
    path('configurations/<int:config_id>/launch-sync/', LaunchSynchronizationView.as_view(), name='launch_synchronization'),

    # Lancer synchronisation métadonnées uniquement
    path('configurations/<int:config_id>/launch-metadata-sync/', LaunchMetadataSyncView.as_view(), name='launch_metadata_sync'),

    # Lancer synchronisation données uniquement
    path('configurations/<int:config_id>/launch-data-sync/', LaunchDataSyncView.as_view(), name='launch_data_sync'),

    # Récupérer les paramètres disponibles pour la synchronisation
    path('configurations/<int:config_id>/sync-parameters/', GetSyncParametersView.as_view(), name='get_sync_parameters'),

    # === JOBS DE SYNCHRONISATION ===
    # Détail d'un job de synchronisation
    path('jobs/<int:job_id>/', SyncJobDetailView.as_view(), name='sync_job_detail'),

    # === SYNCHRONISATION AUTOMATIQUE ===
    # Dashboard de synchronisation automatique
    path('auto-sync/dashboard/', auto_sync.auto_sync_dashboard, name='auto_sync_dashboard'),

    # Paramètres de synchronisation automatique
    path('configurations/<int:config_id>/auto-sync/settings/', auto_sync.auto_sync_settings, name='auto_sync_settings'),

    # Démarrer la synchronisation automatique
    path('configurations/<int:config_id>/auto-sync/start/', auto_sync.start_auto_sync, name='start_auto_sync'),

    # Arrêter la synchronisation automatique
    path('configurations/<int:config_id>/auto-sync/stop/', auto_sync.stop_auto_sync, name='stop_auto_sync'),

    # Redémarrer la synchronisation automatique
    path('configurations/<int:config_id>/auto-sync/restart/', auto_sync.restart_auto_sync, name='restart_auto_sync'),

    # Déclencher une synchronisation immédiate
    path('configurations/<int:config_id>/auto-sync/trigger/', auto_sync.trigger_sync_now, name='trigger_sync_now'),

    # API: Statut d'une configuration
    path('api/auto-sync/<int:config_id>/status/', auto_sync.api_auto_sync_status, name='api_auto_sync_status'),

    # API: Statut de toutes les configurations
    path('api/auto-sync/status/', auto_sync.api_all_auto_sync_status, name='api_all_auto_sync_status'),

    # API: Nettoyage des tâches mortes
    path('api/auto-sync/cleanup/', auto_sync.api_cleanup_tasks, name='api_cleanup_tasks'),

    # API: Progression d'une synchronisation
    path('api/auto-sync/<int:config_id>/progress/', auto_sync.api_sync_progress, name='api_sync_progress'),

    # API: Statistiques globales du dashboard
    path('api/auto-sync/dashboard-stats/', auto_sync.api_dashboard_stats, name='api_dashboard_stats'),

    # === LOGS ===
    # Visualiseur de logs
    path('logs/', logs.logs_viewer, name='logs_viewer'),

    # Logs auto-sync
    path('logs/auto-sync/', logs.auto_sync_logs, name='auto_sync_logs'),

    # Voir un fichier de log
    path('logs/view/<str:log_filename>/', logs.view_log_file, name='view_log_file'),

    # Stream un fichier de log (tail -f)
    path('logs/stream/<str:log_filename>/', logs.stream_log_file, name='stream_log_file'),

    # Télécharger un fichier de log
    path('logs/download/<str:log_filename>/', logs.download_log_file, name='download_log_file'),

    # Vider un fichier de log
    path('logs/clear/<str:log_filename>/', logs.clear_log_file, name='clear_log_file'),

    # Rechercher dans les logs
    path('logs/search/', logs.search_logs, name='search_logs'),
]
