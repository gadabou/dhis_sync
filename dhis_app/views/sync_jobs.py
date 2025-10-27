# -*- coding: utf-8 -*-
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

        return context