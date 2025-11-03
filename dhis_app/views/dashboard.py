"""
Vues pour le tableau de bord général
"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from ..models import DHIS2Instance, SyncConfiguration, SyncJob


class DashboardView(LoginRequiredMixin, TemplateView):
    """Vue principale du tableau de bord"""
    template_name = 'dhis_app/dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Statistiques des instances
        instances = DHIS2Instance.objects.all()
        context['total_instances'] = instances.count()
        context['active_instances'] = instances.filter(is_active=True).count()
        context['source_instances'] = instances.filter(is_source=True).count()
        context['destination_instances'] = instances.filter(is_destination=True).count()

        # Statistiques des configurations
        configs = SyncConfiguration.objects.all()
        context['total_configs'] = configs.count()
        context['active_configs'] = configs.filter(is_active=True).count()

        # Statistiques des jobs (dernières 24h)
        last_24h = timezone.now() - timedelta(hours=24)
        jobs_24h = SyncJob.objects.filter(created_at__gte=last_24h)

        context['jobs_today'] = jobs_24h.count()
        context['jobs_completed'] = jobs_24h.filter(status='completed').count()
        context['jobs_failed'] = jobs_24h.filter(status='failed').count()
        context['jobs_running'] = SyncJob.objects.filter(status='running').count()

        # Jobs récents (derniers 10)
        context['recent_jobs'] = SyncJob.objects.select_related(
            'sync_config',
            'sync_config__source_instance',
            'sync_config__destination_instance'
        ).order_by('-created_at')[:10]

        # Configurations actives
        context['active_configurations'] = SyncConfiguration.objects.filter(
            is_active=True
        ).select_related(
            'source_instance',
            'destination_instance'
        )[:5]

        # Instances avec statut de connexion
        context['instances_status'] = DHIS2Instance.objects.filter(
            is_active=True
        ).order_by('-last_connection_test')[:5]

        # Statistiques par type de sync (dernières 7 jours)
        last_7_days = timezone.now() - timedelta(days=7)
        sync_stats = SyncJob.objects.filter(
            created_at__gte=last_7_days
        ).values('job_type').annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='failed'))
        )
        context['sync_stats'] = list(sync_stats)

        return context