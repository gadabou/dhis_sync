from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse_lazy, reverse
import logging

from ..models import DHIS2Instance

logger = logging.getLogger(__name__)


class DHIS2InstanceListView(LoginRequiredMixin, ListView):
    """Liste toutes les instances DHIS2"""
    model = DHIS2Instance
    template_name = 'dhis_app/dhis2_instance/list.html'
    context_object_name = 'instances'
    ordering = ['-created_at']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Instances DHIS2'
        return context


class DHIS2InstanceDetailView(LoginRequiredMixin, DetailView):
    """Affiche le détail d'une instance DHIS2"""
    model = DHIS2Instance
    template_name = 'dhis_app/dhis2_instance/detail.html'
    context_object_name = 'instance'
    pk_url_kwarg = 'instance_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Instance: {self.object.name}'
        return context


class DHIS2InstanceCreateView(LoginRequiredMixin, CreateView):
    """Créer une nouvelle instance DHIS2"""
    model = DHIS2Instance
    template_name = 'dhis_app/dhis2_instance/form.html'
    fields = ['name', 'base_url', 'username', 'password', 'version', 'is_source', 'is_destination']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Créer une instance DHIS2'
        context['action'] = 'create'
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save()

                # Gérer les requêtes AJAX
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Instance "{self.object.name}" créée avec succès.',
                        'redirect': reverse('dhis2_instance_detail', kwargs={'instance_id': self.object.id})
                    })

                messages.success(self.request, f'Instance "{self.object.name}" créée avec succès.')
                return redirect('dhis2_instance_detail', instance_id=self.object.id)
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
            logger.error(f"Erreur lors de la création de l'instance: {e}")
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

    def get_success_url(self):
        return reverse('dhis2_instance_detail', kwargs={'instance_id': self.object.id})


class DHIS2InstanceUpdateView(LoginRequiredMixin, UpdateView):
    """Modifier une instance DHIS2"""
    model = DHIS2Instance
    template_name = 'dhis_app/dhis2_instance/form.html'
    fields = ['name', 'base_url', 'username', 'password', 'version', 'is_source', 'is_destination']
    pk_url_kwarg = 'instance_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Modifier: {self.object.name}'
        context['action'] = 'edit'
        context['instance'] = self.object
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save()

                # Gérer les requêtes AJAX
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Instance "{self.object.name}" modifiée avec succès.',
                        'redirect': reverse('dhis2_instance_detail', kwargs={'instance_id': self.object.id})
                    })

                messages.success(self.request, f'Instance "{self.object.name}" modifiée avec succès.')
                return redirect('dhis2_instance_detail', instance_id=self.object.id)
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
            logger.error(f"Erreur lors de la modification de l'instance: {e}")
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

    def get_success_url(self):
        return reverse('dhis2_instance_detail', kwargs={'instance_id': self.object.id})


class DHIS2InstanceDeleteView(LoginRequiredMixin, DeleteView):
    """Supprime une instance DHIS2"""
    model = DHIS2Instance
    template_name = 'dhis_app/dhis2_instance/confirm_delete.html'
    context_object_name = 'instance'
    pk_url_kwarg = 'instance_id'
    success_url = reverse_lazy('dhis2_instance_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Supprimer: {self.object.name}'
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        try:
            instance_name = self.object.name

            # Vérifier s'il y a des configurations de sync liées
            source_configs = self.object.source_configs.count()
            dest_configs = self.object.destination_configs.count()

            if source_configs > 0 or dest_configs > 0:
                messages.warning(
                    request,
                    f'Impossible de supprimer "{instance_name}": '
                    f'{source_configs + dest_configs} configuration(s) de synchronisation liée(s).'
                )
                return redirect('dhis2_instance_detail', instance_id=self.object.id)

            success_url = self.get_success_url()
            self.object.delete()
            messages.success(request, f'Instance "{instance_name}" supprimée avec succès.')
            return redirect(success_url)

        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {e}")
            messages.error(request, f'Erreur lors de la suppression: {str(e)}')
            return redirect('dhis2_instance_detail', instance_id=self.object.id)


class DHIS2InstanceToggleStatusView(LoginRequiredMixin, View):
    """Active ou désactive une instance DHIS2"""

    def post(self, request, instance_id):
        instance = get_object_or_404(DHIS2Instance, id=instance_id)

        try:
            action = request.POST.get('action')
            if action == 'activate':
                instance.is_active = True
                status_msg = 'activée'
            elif action == 'deactivate':
                instance.is_active = False
                status_msg = 'désactivée'
            else:
                messages.error(request, 'Action non reconnue.')
                return redirect('dhis2_instance_detail', instance_id=instance_id)

            instance.save()
            messages.success(request, f'Instance "{instance.name}" {status_msg} avec succès.')

        except Exception as e:
            logger.error(f"Erreur lors du changement de statut: {e}")
            messages.error(request, f'Erreur lors du changement de statut: {str(e)}')

        return redirect('dhis2_instance_detail', instance_id=instance_id)


class DHIS2InstanceTestConnectionView(LoginRequiredMixin, View):
    """Test la connexion à une instance DHIS2 (API JSON)"""

    def post(self, request, instance_id):
        instance = get_object_or_404(DHIS2Instance, id=instance_id)

        try:
            result = instance.test_connection()

            if result['success']:
                response_data = {
                    'success': True,
                    'message': result['message'],
                    'details': {
                        'dhis2_version': result.get('dhis2_version'),
                        'system_name': result.get('system_name'),
                        'server_date': result.get('server_date')
                    }
                }

                # Mettre à jour la version si elle n'était pas définie
                if not instance.version and result.get('dhis2_version'):
                    instance.version = result['dhis2_version']
                    instance.save()
                    response_data['version_updated'] = True

            else:
                response_data = {
                    'success': False,
                    'message': result['message']
                }

        except Exception as e:
            logger.error(f"Erreur lors du test de connexion: {e}")
            response_data = {
                'success': False,
                'message': f'Erreur inattendue: {str(e)}'
            }

        return JsonResponse(response_data)


class DHIS2InstanceTestConnectionPageView(LoginRequiredMixin, TemplateView):
    """Page dédiée au test de connexion avec interface"""
    template_name = 'dhis_app/dhis2_instance/test_connection.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance_id = kwargs.get('instance_id')
        context['instance'] = get_object_or_404(DHIS2Instance, id=instance_id)
        context['title'] = f'Test de connexion: {context["instance"].name}'
        context['result'] = None
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        instance = context['instance']

        try:
            result = instance.test_connection()
            context['result'] = result

            if result['success']:
                messages.success(request, 'Connexion réussie!')

                # Mettre à jour la version si elle n'était pas définie
                if not instance.version and result.get('dhis2_version'):
                    instance.version = result['dhis2_version']
                    instance.save()
                    messages.info(request, f'Version DHIS2 mise à jour: {instance.version}')
            else:
                messages.error(request, f'Échec de la connexion: {result["message"]}')

        except Exception as e:
            logger.error(f"Erreur lors du test de connexion: {e}")
            messages.error(request, f'Erreur inattendue: {str(e)}')
            context['result'] = {'success': False, 'message': str(e)}

        return self.render_to_response(context)


class DHIS2InstanceMetadataView(LoginRequiredMixin, TemplateView):
    """Affiche les métadonnées disponibles sur une instance"""
    template_name = 'dhis_app/dhis2_instance/metadata.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance_id = kwargs.get('instance_id')
        context['instance'] = get_object_or_404(DHIS2Instance, id=instance_id)
        context['title'] = f'Métadonnées: {context["instance"].name}'
        context['metadata_info'] = {}
        context['error_message'] = None
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        instance = context['instance']

        try:
            # Test de base pour s'assurer que la connexion fonctionne
            connection_test = instance.test_connection()
            if not connection_test['success']:
                context['error_message'] = f"Connexion échouée: {connection_test['message']}"
            else:
                # Récupérer des informations sur les principales ressources métadonnées
                resources = [
                    'organisationUnits',
                    'dataElements',
                    'indicators',
                    'dataSets',
                    'programs',
                    'users'
                ]

                metadata_info = {}
                for resource in resources:
                    try:
                        # Récupérer juste le count pour avoir une idée du volume
                        api = instance.get_api_client()
                        response = api.get(resource, params={'fields': 'none', 'paging': 'true', 'pageSize': 1})
                        response.raise_for_status()
                        pager_info = response.json().get('pager', {})

                        metadata_info[resource] = {
                            'count': pager_info.get('total', 0),
                            'available': True
                        }
                    except Exception as e:
                        metadata_info[resource] = {
                            'count': 0,
                            'available': False,
                            'error': str(e)
                        }

                context['metadata_info'] = metadata_info

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métadonnées: {e}")
            context['error_message'] = f"Erreur lors de la récupération: {str(e)}"

        return self.render_to_response(context)


class DHIS2InstanceBulkStatusCheckView(LoginRequiredMixin, View):
    """Vérifie l'état de connexion de toutes les instances DHIS2 (API JSON)"""

    def post(self, request):
        try:
            from django.utils import timezone
            instances = DHIS2Instance.objects.filter(is_active=True)
            results = []
            updated_instances = []

            for instance in instances:
                try:
                    # Test de connexion rapide
                    connection_result = instance.test_connection()
                    current_status = connection_result['success']

                    # Si l'état a changé, mettre à jour en base
                    status_changed = instance.connection_status != current_status
                    if status_changed:
                        old_status = instance.connection_status
                        instance.connection_status = current_status
                        instance.last_connection_test = timezone.now()
                        instance.save(update_fields=['connection_status', 'last_connection_test'])
                        updated_instances.append({
                            'id': instance.id,
                            'name': instance.name,
                            'old_status': old_status,
                            'new_status': current_status
                        })

                    results.append({
                        'id': instance.id,
                        'name': instance.name,
                        'status': current_status,
                        'message': connection_result.get('message', ''),
                        'updated': status_changed
                    })

                except Exception as e:
                    logger.error(f"Erreur lors de la vérification de l'instance {instance.name}: {e}")
                    # Marquer comme déconnecté en cas d'erreur
                    if instance.connection_status is not False:
                        instance.connection_status = False
                        instance.last_connection_test = timezone.now()
                        instance.save(update_fields=['connection_status', 'last_connection_test'])
                        updated_instances.append({
                            'id': instance.id,
                            'name': instance.name,
                            'old_status': instance.connection_status,
                            'new_status': False
                        })

                    results.append({
                        'id': instance.id,
                        'name': instance.name,
                        'status': False,
                        'message': f'Erreur: {str(e)}',
                        'updated': True
                    })

            return JsonResponse({
                'success': True,
                'results': results,
                'updated_count': len(updated_instances),
                'updated_instances': updated_instances,
                'total_checked': len(instances)
            })

        except Exception as e:
            logger.error(f"Erreur lors de la vérification bulk des instances: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de la vérification: {str(e)}'
            })
