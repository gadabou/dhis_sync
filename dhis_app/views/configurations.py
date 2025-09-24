# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.http import JsonResponse
from django.views.generic import CreateView, UpdateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
import logging

from ..models import SyncConfiguration, DHIS2Instance, SyncJob
from ..forms import SyncConfigurationForm
from ..services.sync_orchestrator import SyncOrchestrator

logger = logging.getLogger(__name__)


class SyncConfigurationListView(LoginRequiredMixin, ListView):
    """Vue pour lister toutes les configurations de synchronisation"""
    model = SyncConfiguration
    template_name = 'dhis_app/configurations/list.html'
    context_object_name = 'configurations'
    paginate_by = 10

    def get_queryset(self):
        queryset = SyncConfiguration.objects.select_related(
            'source_instance', 'destination_instance', 'created_by'
        ).order_by('-created_at')

        # Filtrage par recherche
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(source_instance__name__icontains=search) |
                Q(destination_instance__name__icontains=search)
            )

        # Filtrage par type de synchronisation
        sync_type = self.request.GET.get('sync_type')
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)

        # Filtrage par statut actif
        is_active = self.request.GET.get('is_active')
        if is_active:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_types'] = SyncConfiguration.SYNC_TYPES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_sync_type'] = self.request.GET.get('sync_type', '')
        context['selected_is_active'] = self.request.GET.get('is_active', '')
        return context


class SyncConfigurationDetailView(LoginRequiredMixin, DetailView):
    """Vue pour voir les details d'une configuration"""
    model = SyncConfiguration
    template_name = 'dhis_app/configurations/detail.html'
    context_object_name = 'configuration'
    pk_url_kwarg = 'config_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = self.object

        # Statistiques des jobs récents
        recent_jobs = config.jobs.order_by('-created_at')[:10]
        context['recent_jobs'] = recent_jobs

        # Statistiques globales
        all_jobs = config.jobs.all()
        context['total_jobs'] = all_jobs.count()
        context['successful_jobs'] = all_jobs.filter(status='completed').count()
        context['failed_jobs'] = all_jobs.filter(status='failed').count()

        # Informations de compatibilité
        context['compatibility_info'] = self.get_compatibility_info(config)

        # Étapes d'orchestration si applicable
        if config.is_composite_sync:
            context['orchestration_steps'] = config.get_orchestration_steps()

        return context

    def get_compatibility_info(self, config):
        """Vérifie la compatibilité entre source et destination"""
        try:
            source_api = config.source_instance.get_api_client()
            dest_api = config.destination_instance.get_api_client()

            # Test de connexion basique
            source_info = source_api.get('system/info').json() if source_api else None
            dest_info = dest_api.get('system/info').json() if dest_api else None

            compatibility = {
                'source_available': source_info is not None,
                'dest_available': dest_info is not None,
                'source_version': source_info.get('version') if source_info else 'Inconnue',
                'dest_version': dest_info.get('version') if dest_info else 'Inconnue',
                'versions_compatible': True,  # À implémenter selon les besoins
                'warnings': [],
                'errors': []
            }

            # Vérifications de compatibilité
            if source_info and dest_info:
                source_version = source_info.get('version', '')
                dest_version = dest_info.get('version', '')

                # Avertissement si versions très différentes
                if source_version and dest_version:
                    source_major = source_version.split('.')[0] if '.' in source_version else source_version
                    dest_major = dest_version.split('.')[0] if '.' in dest_version else dest_version

                    if source_major != dest_major:
                        compatibility['warnings'].append(
                            f"Versions majeures différentes: {source_version} → {dest_version}"
                        )

            return compatibility

        except Exception as e:
            logger.error(f"Erreur lors de la vérification de compatibilité: {e}")
            return {
                'source_available': False,
                'dest_available': False,
                'source_version': 'Erreur',
                'dest_version': 'Erreur',
                'versions_compatible': False,
                'warnings': [],
                'errors': [str(e)]
            }


class SyncConfigurationCreateView(LoginRequiredMixin, CreateView):
    """Vue pour créer une nouvelle configuration de synchronisation"""
    model = SyncConfiguration
    form_class = SyncConfigurationForm
    template_name = 'dhis_app/configurations/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Créer une configuration de synchronisation'
        context['form_action'] = reverse('sync_config_create')
        context['breadcrumb'] = [
            {'name': 'Configurations', 'url': reverse('sync_config_list')},
            {'name': 'Nouvelle configuration', 'url': None}
        ]
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                form.instance.created_by = self.request.user
                self.object = form.save()

                # Gérer les requêtes AJAX
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Configuration "{self.object.name}" créée avec succès.',
                        'redirect': reverse('sync_config_detail', kwargs={'config_id': self.object.id})
                    })

                messages.success(self.request, f'Configuration "{self.object.name}" créée avec succès.')
                return redirect('sync_config_detail', config_id=self.object.id)

        except ValidationError as e:
            error_dict = {}
            if hasattr(e, 'message_dict'):
                error_dict = e.message_dict
                if not self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            messages.error(self.request, f'{field}: {error}')
            else:
                error_message = str(e)
                if not self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    messages.error(self.request, error_message)
                else:
                    error_dict = {'__all__': [error_message]}

            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': error_dict
                })
            return self.form_invalid(form)

        except Exception as e:
            logger.error(f"Erreur lors de la création de la configuration: {e}")
            error_message = f'Erreur lors de la création: {str(e)}'

            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })

            messages.error(self.request, error_message)
            return self.form_invalid(form)

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        return super().form_invalid(form)


class SyncConfigurationUpdateView(LoginRequiredMixin, UpdateView):
    """Vue pour modifier une configuration de synchronisation"""
    model = SyncConfiguration
    form_class = SyncConfigurationForm
    template_name = 'dhis_app/configurations/form.html'
    pk_url_kwarg = 'config_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Modifier la configuration "{self.object.name}"'
        context['form_action'] = reverse('sync_config_update', kwargs={'config_id': self.object.id})
        context['breadcrumb'] = [
            {'name': 'Configurations', 'url': reverse('sync_config_list')},
            {'name': self.object.name, 'url': reverse('sync_config_detail', kwargs={'config_id': self.object.id})},
            {'name': 'Modifier', 'url': None}
        ]
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save()

                # Gérer les requêtes AJAX
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Configuration "{self.object.name}" modifiée avec succès.',
                        'redirect': reverse('sync_config_detail', kwargs={'config_id': self.object.id})
                    })

                messages.success(self.request, f'Configuration "{self.object.name}" modifiée avec succès.')
                return redirect('sync_config_detail', config_id=self.object.id)

        except ValidationError as e:
            error_dict = {}
            if hasattr(e, 'message_dict'):
                error_dict = e.message_dict
                if not self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            messages.error(self.request, f'{field}: {error}')
            else:
                error_message = str(e)
                if not self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    messages.error(self.request, error_message)
                else:
                    error_dict = {'__all__': [error_message]}

            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': error_dict
                })
            return self.form_invalid(form)

        except Exception as e:
            logger.error(f"Erreur lors de la modification de la configuration: {e}")
            error_message = f'Erreur lors de la modification: {str(e)}'

            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })

            messages.error(self.request, error_message)
            return self.form_invalid(form)

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        return super().form_invalid(form)


class ToggleConfigurationStatusView(LoginRequiredMixin, View):
    """Vue pour activer/désactiver une configuration"""

    def post(self, request, config_id):
        config = get_object_or_404(SyncConfiguration, id=config_id)

        try:
            # Inverser le statut
            config.is_active = not config.is_active
            config.save()

            status = 'activée' if config.is_active else 'désactivée'
            message = f'Configuration "{config.name}" {status} avec succès.'

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'is_active': config.is_active
                })

            messages.success(request, message)
            return redirect('sync_config_detail', config_id=config.id)

        except Exception as e:
            logger.error(f"Erreur lors du changement de statut: {e}")
            error_message = f'Erreur: {str(e)}'

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })

            messages.error(request, error_message)
            return redirect('sync_config_detail', config_id=config.id)

    def get(self, request, config_id):
        return redirect('sync_config_detail', config_id=config_id)


class TestConfigurationCompatibilityView(LoginRequiredMixin, View):
    """Vue pour tester la compatibilité entre source et destination"""

    def post(self, request, config_id):
        config = get_object_or_404(SyncConfiguration, id=config_id)

        try:
            # Test de connexion aux deux instances
            source_result = config.source_instance.test_connection()
            dest_result = config.destination_instance.test_connection()

            compatibility_result = {
                'success': source_result['success'] and dest_result['success'],
                'source_test': source_result,
                'destination_test': dest_result,
                'compatibility_checks': [],
                'warnings': [],
                'recommendations': []
            }

            # Vérifications de compatibilité détaillées
            if source_result['success'] and dest_result['success']:
                source_version = source_result.get('dhis2_version', '')
                dest_version = dest_result.get('dhis2_version', '')

                # Comparaison des versions
                if source_version and dest_version:
                    if source_version == dest_version:
                        compatibility_result['compatibility_checks'].append({
                            'check': 'Version DHIS2',
                            'status': 'success',
                            'message': f'Versions identiques: {source_version}'
                        })
                    else:
                        compatibility_result['compatibility_checks'].append({
                            'check': 'Version DHIS2',
                            'status': 'warning',
                            'message': f'Versions différentes: {source_version} → {dest_version}'
                        })
                        compatibility_result['warnings'].append(
                            'Les versions DHIS2 différentes peuvent causer des problèmes de compatibilité'
                        )

                # Recommandations basées sur le type de sync
                if config.sync_type == 'complete':
                    compatibility_result['recommendations'].append(
                        'Synchronisation complète: Assurez-vous que la destination peut recevoir de gros volumes de données'
                    )
                elif config.sync_type == 'metadata':
                    compatibility_result['recommendations'].append(
                        'Synchronisation métadonnées: Vérifiez que les structures sont compatibles entre les versions'
                    )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(compatibility_result)

            # Pour les requêtes non-AJAX, rediriger avec un message
            if compatibility_result['success']:
                messages.success(request, 'Test de compatibilité réussi.')
            else:
                messages.error(request, 'Test de compatibilité échoué.')

            return redirect('sync_config_detail', config_id=config.id)

        except Exception as e:
            logger.error(f"Erreur lors du test de compatibilité: {e}")
            error_result = {
                'success': False,
                'message': f'Erreur lors du test: {str(e)}'
            }

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(error_result)

            messages.error(request, error_result['message'])
            return redirect('sync_config_detail', config_id=config.id)

    def get(self, request, config_id):
        return redirect('sync_config_detail', config_id=config_id)


class CloneConfigurationView(LoginRequiredMixin, View):
    """Vue pour cloner une configuration existante"""

    def post(self, request, config_id):
        original_config = get_object_or_404(SyncConfiguration, id=config_id)

        try:
            with transaction.atomic():
                # Créer une copie de la configuration
                cloned_config = SyncConfiguration.objects.create(
                    name=f"{original_config.name} (Copie)",
                    source_instance=original_config.source_instance,
                    destination_instance=original_config.destination_instance,
                    sync_type=original_config.sync_type,
                    data_type=original_config.data_type,
                    import_strategy=original_config.import_strategy,
                    merge_mode=original_config.merge_mode,
                    execution_mode=original_config.execution_mode,
                    max_page_size=original_config.max_page_size,
                    supports_paging=original_config.supports_paging,
                    is_active=False,  # La copie est inactive par défaut
                    schedule_enabled=False,  # Désactiver la planification
                    schedule_interval=original_config.schedule_interval,
                    sync_start_date=original_config.sync_start_date,
                    sync_end_date=original_config.sync_end_date,
                    created_by=request.user
                )

                message = f'Configuration "{original_config.name}" clonée avec succès.'

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': message,
                        'redirect': reverse('sync_config_detail', kwargs={'config_id': cloned_config.id})
                    })

                messages.success(request, message)
                return redirect('sync_config_detail', config_id=cloned_config.id)

        except Exception as e:
            logger.error(f"Erreur lors du clonage: {e}")
            error_message = f'Erreur lors du clonage: {str(e)}'

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })

            messages.error(request, error_message)
            return redirect('sync_config_detail', config_id=config_id)

    def get(self, request, config_id):
        return redirect('sync_config_detail', config_id=config_id)

