# -*- coding: utf-8 -*-
import re
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from ..models import SyncJob


class SyncJobDetailView(LoginRequiredMixin, DetailView):
    """Vue pour voir les details d'un job de synchronisation"""
    model = SyncJob
    template_name = 'dhis_app/sync_jobs/detail.html'
    context_object_name = 'job'
    pk_url_kwarg = 'job_id'

    def parse_sync_stats(self, log_message):
        """
        Parse les logs pour extraire les statistiques de métadonnées et données

        Returns:
            tuple: (metadata_stats, data_stats)
            metadata_stats: dict avec les stats par type de métadonnées
            data_stats: dict avec les stats par type de données
        """
        metadata_stats = []
        data_stats = []

        if not log_message:
            return metadata_stats, data_stats

        # Liste des types de métadonnées et données
        metadata_types = [
            'userGroups', 'userRoles', 'users',
            'organisationUnitLevels', 'organisationUnits', 'organisationUnitGroups', 'organisationUnitGroupSets',
            'categoryOptions', 'categories', 'categoryCombos', 'categoryOptionGroups', 'categoryOptionGroupSets',
            'options', 'optionSets',
            'attributes', 'constants',
            'dataElements', 'dataElementGroups', 'dataElementGroupSets',
            'indicatorTypes', 'indicators', 'indicatorGroups', 'indicatorGroupSets',
            'dataEntryForms', 'dataSets', 'dataSetElements', 'dataInputPeriods', 'dataSetNotificationTemplates',
            'trackedEntityTypes', 'trackedEntityAttributes', 'trackedEntityAttributeGroups',
            'relationshipTypes',
            'programs', 'programStages', 'programStageSections', 'programStageDataElements',
            'programRuleActions', 'programIndicators', 'programRuleVariables', 'programRules', 'programNotificationTemplates',
            'validationRules', 'validationRuleGroups', 'validationNotificationTemplates',
            'predictors', 'predictorGroups',
            'legends', 'legendSets',
            'maps', 'visualizations', 'eventReports', 'dashboards',
            'documents', 'interpretations'
        ]

        data_types_keywords = ['Données agrégées', 'événements', 'tracker', 'Programme']

        # Pattern pour extraire les stats: ✓ resource: Source=X | Created=Y, Updated=Z | Ignored=W | Errors=E
        pattern = r'✓\s+(\w+):\s+Source=(\d+)\s+\|\s+Created=(\d+),\s+Updated=(\d+)\s+\|\s+Ignored=(\d+)\s+\|\s+Errors=(\d+)'

        # Pattern alternatif pour les nouvelles lignes
        pattern_alt = r'(\w+)\s+\((\d+)\)\s+-\s+Récupérés:\s+(\d+),\s+Créés:\s+(\d+),\s+Modifiés:\s+(\d+),\s+Erreurs:\s+(\d+),\s+Ignorés:\s+(\d+)'

        # Pattern pour les données (programmes, events)
        data_pattern = r'Programme\s+\w+:\s+Source=(\d+)\s+\|\s+Created=(\d+),\s+Updated=(\d+)\s+\|\s+Ignored=(\d+)\s+\|\s+Errors=(\d+)'
        event_pattern = r'✓\s+Programme\s+(\w+):\s+Source=(\d+)\s+\|\s+Created=(\d+),\s+Updated=(\d+)\s+\|\s+Ignored=(\d+)\s+\|\s+Errors=(\d+)'

        lines = log_message.split('\n')

        for line in lines:
            # Essayer le premier pattern
            match = re.search(pattern, line)
            if match:
                resource_name = match.group(1)
                source_count = int(match.group(2))
                created = int(match.group(3))
                updated = int(match.group(4))
                ignored = int(match.group(5))
                errors = int(match.group(6))

                # Calculer la progression (100% si tout est traité)
                total_processed = created + updated + ignored + errors
                if source_count > 0:
                    progress = int((total_processed / source_count) * 100)
                else:
                    progress = 100 if total_processed > 0 else 0

                stat = {
                    'name': resource_name,
                    'progress': progress,
                    'total': source_count,
                    'created': created,
                    'updated': updated,
                    'errors': errors,
                    'ignored': ignored
                }

                # Classifier en métadonnées ou données
                if resource_name in metadata_types:
                    metadata_stats.append(stat)
                else:
                    data_stats.append(stat)
                continue

            # Essayer le pattern pour les événements de programmes
            match = re.search(event_pattern, line)
            if match:
                program_uid = match.group(1)
                source_count = int(match.group(2))
                created = int(match.group(3))
                updated = int(match.group(4))
                ignored = int(match.group(5))
                errors = int(match.group(6))

                total_processed = created + updated + ignored + errors
                if source_count > 0:
                    progress = int((total_processed / source_count) * 100)
                else:
                    progress = 100 if total_processed > 0 else 0

                data_stats.append({
                    'name': f'Programme {program_uid}',
                    'progress': progress,
                    'total': source_count,
                    'created': created,
                    'updated': updated,
                    'errors': errors,
                    'ignored': ignored
                })

        return metadata_stats, data_stats

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.object

        # Calculer la duree
        if job.started_at and job.completed_at:
            duration = job.completed_at - job.started_at
            context['duration'] = duration
        elif job.started_at:
            from django.utils import timezone
            duration = timezone.now() - job.started_at
            context['duration'] = duration
        else:
            context['duration'] = None

        # Parser les statistiques détaillées
        metadata_stats, data_stats = self.parse_sync_stats(job.log_message)
        context['metadata_stats'] = metadata_stats
        context['data_stats'] = data_stats

        return context