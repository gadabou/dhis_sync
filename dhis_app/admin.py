from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
import csv
import json
from datetime import datetime
from .models import (
    DHIS2Instance, SyncConfiguration, MetadataType, SyncJob,
    AutoSyncSettings, DHIS2Entity, DHIS2EntityVersion, DateFilterAttribute
)


class ExportMixin:
    """Mixin pour ajouter des fonctionnalités d'export aux admins"""

    def export_csv(self, request, queryset):
        """Exporte les données sélectionnées en CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.model._meta.verbose_name_plural}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)

        # En-têtes
        fields = [field.name for field in self.model._meta.fields]
        writer.writerow(fields)

        # Données
        for obj in queryset:
            row = []
            for field in fields:
                value = getattr(obj, field)
                if hasattr(value, 'strftime'):  # DateTime
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                elif hasattr(value, 'all'):  # ManyToMany
                    value = ', '.join(str(v) for v in value.all())
                row.append(str(value) if value is not None else '')
            writer.writerow(row)

        return response
    export_csv.short_description = "Exporter en CSV"

    def export_json(self, request, queryset):
        """Exporte les données sélectionnées en JSON"""
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{self.model._meta.verbose_name_plural}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'

        data = []
        for obj in queryset:
            item = {}
            for field in self.model._meta.fields:
                value = getattr(obj, field.name)
                if hasattr(value, 'strftime'):  # DateTime
                    value = value.isoformat()
                elif hasattr(value, 'pk'):  # ForeignKey
                    value = value.pk
                item[field.name] = value
            data.append(item)

        json.dump(data, response, indent=2, ensure_ascii=False)
        return response
    export_json.short_description = "Exporter en JSON"


@admin.register(DHIS2Instance)
class DHIS2InstanceAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['name', 'base_url', 'username', 'version', 'is_source', 'is_destination', 'created_at']
    list_filter = ['is_source', 'is_destination', 'version', 'created_at']
    search_fields = ['name', 'base_url', 'username']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['export_csv', 'export_json']

    fieldsets = [
        ('Informations de base', {
            'fields': ['name', 'base_url', 'username', 'password', 'version']
        }),
        ('Type d\'instance', {
            'fields': ['is_source', 'is_destination']
        }),
        ('Métadonnées', {
            'fields': ['created_at', 'updated_at']
        }),
    ]


@admin.register(SyncConfiguration)
class SyncConfigurationAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['name', 'source_instance', 'destination_instance', 'sync_type', 'data_type', 'is_active', 'schedule_enabled', 'created_by']
    list_filter = ['sync_type', 'data_type', 'is_active', 'schedule_enabled', 'created_at']
    search_fields = ['name', 'source_instance__name', 'destination_instance__name']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['export_csv', 'export_json', 'activate_configs', 'deactivate_configs']

    fieldsets = [
        ('Configuration de base', {
            'fields': ['name', 'source_instance', 'destination_instance', 'created_by']
        }),
        ('Type de synchronisation', {
            'fields': ['sync_type', 'data_type']
        }),
        ('Planification', {
            'fields': ['is_active', 'schedule_enabled', 'schedule_interval']
        }),
        ('Métadonnées', {
            'fields': ['created_at', 'updated_at']
        }),
    ]

    def activate_configs(self, request, queryset):
        """Active les configurations sélectionnées"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} configurations activées.')
    activate_configs.short_description = "Activer les configurations"

    def deactivate_configs(self, request, queryset):
        """Désactive les configurations sélectionnées"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} configurations désactivées.')
    deactivate_configs.short_description = "Désactiver les configurations"


@admin.register(MetadataType)
class MetadataTypeAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['name', 'api_endpoint', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'api_endpoint']
    actions = ['export_csv', 'export_json', 'activate_types', 'deactivate_types']

    def activate_types(self, request, queryset):
        """Active les types de métadonnées sélectionnés"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} types de métadonnées activés.')
    activate_types.short_description = "Activer les types"

    def deactivate_types(self, request, queryset):
        """Désactive les types de métadonnées sélectionnés"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} types de métadonnées désactivés.')
    deactivate_types.short_description = "Désactiver les types"


@admin.register(SyncJob)
class SyncJobAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['id', 'display_name', 'job_type', 'status', 'progress_percentage', 'success_count', 'error_count', 'started_at', 'completed_at']
    list_filter = ['status', 'job_type', 'created_at', 'sync_config']
    search_fields = ['sync_config__name', 'log_message']
    readonly_fields = ['created_at', 'progress_percentage', 'display_name']
    actions = ['export_csv', 'export_json', 'cancel_jobs', 'retry_failed_jobs']

    fieldsets = [
        ('Informations de base', {
            'fields': ['sync_config', 'job_type', 'status', 'display_name']
        }),
        ('Progression', {
            'fields': ['progress', 'total_items', 'processed_items', 'success_count', 'error_count', 'warning_count']
        }),
        ('Dates', {
            'fields': ['started_at', 'completed_at', 'created_at']
        }),
        ('Retry', {
            'fields': ['retry_count', 'max_retries', 'last_error', 'next_retry_at', 'parent_job', 'is_retry']
        }),
        ('Journal', {
            'fields': ['log_message']
        }),
    ]

    def cancel_jobs(self, request, queryset):
        """Annule les jobs sélectionnés"""
        count = queryset.filter(status__in=['pending', 'running']).update(status='cancelled')
        self.message_user(request, f'{count} jobs annulés.')
    cancel_jobs.short_description = "Annuler les jobs"

    def retry_failed_jobs(self, request, queryset):
        """Relance les jobs échoués sélectionnés"""
        count = 0
        for job in queryset.filter(status='failed'):
            if job.can_retry():
                job.schedule_retry()
                count += 1
        self.message_user(request, f'{count} jobs programmés pour retry.')
    retry_failed_jobs.short_description = "Programmer retry des jobs échoués"


@admin.register(DHIS2Entity)
class DHIS2EntityAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['name', 'entity_type', 'dhis2_uid', 'sync_config', 'is_selected', 'sync_status', 'import_order', 'last_synchronized']
    list_filter = ['entity_type', 'sync_status', 'is_selected', 'sync_config', 'created_at']
    search_fields = ['name', 'dhis2_uid', 'display_name', 'code']
    readonly_fields = ['created_at', 'updated_at', 'import_order']
    actions = ['export_csv', 'export_json', 'select_entities', 'deselect_entities', 'reset_sync_status']

    fieldsets = [
        ('Informations DHIS2', {
            'fields': ['entity_type', 'dhis2_uid', 'name', 'display_name', 'short_name', 'code']
        }),
        ('Configuration de sync', {
            'fields': ['sync_config', 'is_selected', 'import_order']
        }),
        ('État de synchronisation', {
            'fields': ['sync_status', 'last_synchronized', 'sync_error_message']
        }),
        ('Versions et mapping', {
            'fields': ['source_version_info', 'destination_version_info', 'field_mapping', 'data_transformations']
        }),
        ('Métadonnées', {
            'fields': ['created_at', 'updated_at']
        }),
    ]

    def select_entities(self, request, queryset):
        """Sélectionne les entités pour la synchronisation"""
        count = queryset.update(is_selected=True)
        self.message_user(request, f'{count} entités sélectionnées pour la synchronisation.')
    select_entities.short_description = "Sélectionner pour la synchronisation"

    def deselect_entities(self, request, queryset):
        """Désélectionne les entités de la synchronisation"""
        count = queryset.update(is_selected=False)
        self.message_user(request, f'{count} entités désélectionnées de la synchronisation.')
    deselect_entities.short_description = "Désélectionner de la synchronisation"

    def reset_sync_status(self, request, queryset):
        """Remet à zéro le statut de synchronisation"""
        count = queryset.update(sync_status='pending', sync_error_message='', last_synchronized=None)
        self.message_user(request, f'Statut de synchronisation remis à zéro pour {count} entités.')
    reset_sync_status.short_description = "Remettre à zéro le statut de sync"


@admin.register(DHIS2EntityVersion)
class DHIS2EntityVersionAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['dhis2_version', 'entity_type', 'api_endpoint', 'max_page_size', 'supports_bulk_import', 'import_strategy', 'is_active']
    list_filter = ['dhis2_version', 'entity_type', 'supports_bulk_import', 'supports_upsert', 'import_strategy', 'is_active']
    search_fields = ['dhis2_version', 'entity_type', 'api_endpoint']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['export_csv', 'export_json', 'activate_versions', 'deactivate_versions']

    fieldsets = [
        ('Informations de base', {
            'fields': ['dhis2_version', 'entity_type', 'is_active']
        }),
        ('Configuration API', {
            'fields': ['api_endpoint', 'api_path', 'max_page_size', 'supports_paging']
        }),
        ('Champs supportés', {
            'fields': ['supported_fields', 'required_fields', 'deprecated_fields', 'new_fields']
        }),
        ('Import/Export', {
            'fields': ['supports_bulk_import', 'supports_upsert', 'import_strategy']
        }),
        ('Validation', {
            'fields': ['validation_rules']
        }),
        ('Métadonnées', {
            'fields': ['notes', 'created_at', 'updated_at']
        }),
    ]

    def activate_versions(self, request, queryset):
        """Active les versions sélectionnées"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} versions activées.')
    activate_versions.short_description = "Activer les versions"

    def deactivate_versions(self, request, queryset):
        """Désactive les versions sélectionnées"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} versions désactivées.')
    deactivate_versions.short_description = "Désactiver les versions"


@admin.register(DateFilterAttribute)
class DateFilterAttributeAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['program_name', 'program_uid', 'filter_type', 'date_attribute_name', 'date_attribute_uid', 'dhis2_instance']
    list_filter = ['filter_type', 'dhis2_instance', 'created_at']
    search_fields = ['program_name', 'program_uid', 'date_attribute_name', 'date_attribute_uid']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['export_csv', 'export_json']

    fieldsets = [
        ('Instance DHIS2', {
            'fields': ['dhis2_instance']
        }),
        ('Configuration du programme', {
            'fields': ['filter_type', 'program_uid', 'program_name']
        }),
        ('Attribut de date', {
            'fields': ['date_attribute_uid', 'date_attribute_name', 'default_to_created']
        }),
        ('Métadonnées', {
            'fields': ['created_at', 'updated_at']
        }),
    ]


@admin.register(AutoSyncSettings)
class AutoSyncSettingsAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['sync_config', 'is_enabled', 'check_interval', 'high_frequency_mode', 'monitor_metadata', 'monitor_data_values']
    list_filter = ['is_enabled', 'high_frequency_mode', 'monitor_metadata', 'monitor_data_values']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['export_csv', 'export_json', 'enable_auto_sync', 'disable_auto_sync']

    fieldsets = [
        ('Configuration de base', {
            'fields': ['sync_config', 'is_enabled', 'check_interval']
        }),
        ('Mode haute fréquence', {
            'fields': ['high_frequency_mode', 'high_frequency_interval', 'high_frequency_resources']
        }),
        ('Surveillance', {
            'fields': ['monitor_metadata', 'monitor_data_values', 'metadata_resources', 'exclude_resources']
        }),
        ('Déclenchement automatique', {
            'fields': ['immediate_sync', 'delay_before_sync']
        }),
        ('Limites de sécurité', {
            'fields': ['max_sync_per_hour', 'cooldown_after_error']
        }),
        ('Notifications', {
            'fields': ['notify_on_change', 'notify_on_sync_start', 'notify_on_sync_complete']
        }),
        ('Métadonnées', {
            'fields': ['created_at', 'updated_at']
        }),
    ]

    def enable_auto_sync(self, request, queryset):
        """Active la synchronisation automatique"""
        count = queryset.update(is_enabled=True)
        self.message_user(request, f'Synchronisation automatique activée pour {count} configurations.')
    enable_auto_sync.short_description = "Activer la sync automatique"

    def disable_auto_sync(self, request, queryset):
        """Désactive la synchronisation automatique"""
        count = queryset.update(is_enabled=False)
        self.message_user(request, f'Synchronisation automatique désactivée pour {count} configurations.')
    disable_auto_sync.short_description = "Désactiver la sync automatique"
