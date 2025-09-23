from django.urls import path
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
)
from .views.configurations import (
    SyncConfigurationListView,
    SyncConfigurationDetailView,
    SyncConfigurationCreateView,
    SyncConfigurationUpdateView,
    toggle_configuration_status,
    test_configuration_compatibility,
    clone_configuration,
)

urlpatterns = [
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
    path('configurations/<int:config_id>/toggle-status/', toggle_configuration_status, name='sync_config_toggle_status'),

    # Test de compatibilité
    path('configurations/<int:config_id>/test-compatibility/', test_configuration_compatibility, name='sync_config_test_compatibility'),

    # Cloner une configuration
    path('configurations/<int:config_id>/clone/', clone_configuration, name='sync_config_clone'),
]
