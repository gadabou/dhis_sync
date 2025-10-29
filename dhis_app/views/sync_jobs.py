# -*- coding: utf-8 -*-
import re
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
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

        # Pattern pour les chunks (dataValues): Chunk X/Y: A importés, B mis à jour, C ignorés
        chunk_pattern = r'Chunk\s+\d+/\d+:\s+(\d+)\s+importés,\s+(\d+)\s+mis à jour,\s+(\d+)\s+ignorés'

        # Pattern pour récupérer le total de dataValues
        datavalues_total_pattern = r'Trouvé\s+(\d+)\s+valeurs de données'

        # Pattern pour compter les erreurs de chunks
        chunk_error_pattern = r'ERREUR:\s+Erreur import chunk'

        # Pattern pour les données (programmes, events)
        event_pattern = r'✓\s+Programme\s+(\w+):\s+Source=(\d+)\s+\|\s+Created=(\d+),\s+Updated=(\d+)\s+\|\s+Ignored=(\d+)\s+\|\s+Errors=(\d+)'

        lines = log_message.split('\n')

        # Variables pour agréger les chunks de dataValues
        datavalues_total = 0
        datavalues_imported = 0
        datavalues_updated = 0
        datavalues_ignored = 0
        datavalues_errors = 0
        datavalues_found = False

        for line in lines:
            # Détecter le total de dataValues
            match = re.search(datavalues_total_pattern, line)
            if match:
                datavalues_total = int(match.group(1))
                datavalues_found = True
                continue

            # Agréger les chunks de dataValues
            match = re.search(chunk_pattern, line)
            if match:
                datavalues_imported += int(match.group(1))
                datavalues_updated += int(match.group(2))
                datavalues_ignored += int(match.group(3))
                continue

            # Compter les erreurs de chunks
            if re.search(chunk_error_pattern, line):
                datavalues_errors += 1
                continue

            # Essayer le premier pattern (métadonnées)
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

        # Ajouter les dataValues agrégées si trouvées
        if datavalues_found:
            # Calculer la progression
            total_processed = datavalues_imported + datavalues_updated + datavalues_ignored + datavalues_errors
            if datavalues_total > 0:
                progress = min(100, int((total_processed / datavalues_total) * 100))
            else:
                progress = 100

            data_stats.append({
                'name': 'dataValues',
                'progress': progress,
                'total': datavalues_total,
                'created': datavalues_imported,
                'updated': datavalues_updated,
                'errors': datavalues_errors,
                'ignored': datavalues_ignored
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


@login_required
@require_http_methods(["GET"])
def sync_job_stats_api(request, job_id):
    """
    API pour récupérer les statistiques d'un job en temps réel (sans recharger la page)
    """
    job = get_object_or_404(SyncJob, id=job_id)

    # Parser les stats
    view = SyncJobDetailView()
    metadata_stats, data_stats = view.parse_sync_stats(job.log_message)

    # Calculer la durée
    duration_seconds = None
    if job.started_at:
        from django.utils import timezone
        if job.completed_at:
            duration = job.completed_at - job.started_at
        else:
            duration = timezone.now() - job.started_at
        duration_seconds = int(duration.total_seconds())

    return JsonResponse({
        'status': job.status,
        'progress': job.progress,
        'total_items': job.total_items,
        'success_count': job.success_count,
        'error_count': job.error_count,
        'warning_count': job.warning_count,
        'metadata_stats': metadata_stats,
        'data_stats': data_stats,
        'duration_seconds': duration_seconds,
        'is_running': job.status == 'running'
    })