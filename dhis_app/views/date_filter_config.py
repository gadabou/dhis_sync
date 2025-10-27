from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
import logging

from ..models import DHIS2Instance, DateFilterAttribute

logger = logging.getLogger(__name__)


@login_required
def date_filter_config_view(request):
    """
    Page de configuration des attributs de filtre de date.
    Permet de sélectionner une instance source et configurer les attributs
    de date pour chaque programme.
    """
    # Récupérer toutes les instances sources
    source_instances = DHIS2Instance.objects.filter(is_source=True)

    # Instance sélectionnée (depuis le formulaire ou None)
    selected_instance_id = request.GET.get('instance_id')
    selected_instance = None

    if selected_instance_id:
        try:
            selected_instance = DHIS2Instance.objects.get(id=selected_instance_id, is_source=True)
        except DHIS2Instance.DoesNotExist:
            messages.error(request, "Instance source non trouvée.")

    # Récupérer les configurations existantes pour l'instance sélectionnée
    existing_configs = []
    if selected_instance:
        existing_configs = DateFilterAttribute.objects.filter(
            dhis2_instance=selected_instance
        ).values('program_uid', 'program_name', 'date_attribute_uid', 'date_attribute_name', 'filter_type')

    context = {
        'source_instances': source_instances,
        'selected_instance': selected_instance,
        'existing_configs': list(existing_configs),
    }

    return render(request, 'dhis_app/date_filter_config.html', context)


@login_required
@require_http_methods(["POST"])
def save_date_filter_configs(request):
    """
    Sauvegarde les configurations d'attributs de filtre de date.
    Reçoit un JSON avec les configurations pour tous les programmes.
    """
    try:
        import json
        data = json.loads(request.body)

        instance_id = data.get('instance_id')
        configs = data.get('configs', [])

        if not instance_id:
            return JsonResponse({'success': False, 'error': 'Instance ID manquant'}, status=400)

        # Récupérer l'instance
        try:
            instance = DHIS2Instance.objects.get(id=instance_id, is_source=True)
        except DHIS2Instance.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Instance source non trouvée'}, status=404)

        # Sauvegarder les configurations dans une transaction
        with transaction.atomic():
            # Supprimer les anciennes configurations pour cette instance
            DateFilterAttribute.objects.filter(dhis2_instance=instance).delete()

            # Créer les nouvelles configurations
            created_count = 0
            for config in configs:
                # Vérifier que les champs requis sont présents
                if not config.get('program_uid') or not config.get('date_attribute_uid'):
                    continue

                DateFilterAttribute.objects.create(
                    dhis2_instance=instance,
                    filter_type=config.get('filter_type', 'event'),
                    program_uid=config['program_uid'],
                    program_name=config.get('program_name', ''),
                    date_attribute_uid=config['date_attribute_uid'],
                    date_attribute_name=config.get('date_attribute_name', ''),
                    default_to_created=True
                )
                created_count += 1

        return JsonResponse({
            'success': True,
            'message': f'{created_count} configuration(s) sauvegardée(s) avec succès'
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des configurations: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_programs_api(request):
    """
    API pour récupérer les programmes d'une instance DHIS2.
    """
    instance_id = request.GET.get('instance_id')

    if not instance_id:
        return JsonResponse({'success': False, 'error': 'Instance ID manquant'}, status=400)

    try:
        instance = DHIS2Instance.objects.get(id=instance_id, is_source=True)
    except DHIS2Instance.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Instance source non trouvée'}, status=404)

    try:
        # Récupérer les programmes depuis DHIS2
        programs = instance.get_metadata(
            resource='programs',
            fields='id,name,displayName,programType',
            paging=False
        )

        # Formater les données
        formatted_programs = []
        for program in programs:
            program_type = program.get('programType', 'WITH_REGISTRATION')
            filter_type = 'tracker' if program_type == 'WITH_REGISTRATION' else 'event'

            formatted_programs.append({
                'uid': program.get('id'),
                'name': program.get('displayName') or program.get('name'),
                'programType': program_type,
                'filter_type': filter_type
            })

        return JsonResponse({
            'success': True,
            'programs': formatted_programs
        })

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des programmes: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors de la récupération des programmes: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_date_attributes_api(request):
    """
    API pour récupérer les attributs/dataElements de type date d'un programme.
    """
    instance_id = request.GET.get('instance_id')
    program_uid = request.GET.get('program_uid')
    filter_type = request.GET.get('filter_type', 'event')

    if not instance_id or not program_uid:
        return JsonResponse({
            'success': False,
            'error': 'Instance ID et Program UID sont requis'
        }, status=400)

    try:
        instance = DHIS2Instance.objects.get(id=instance_id, is_source=True)
    except DHIS2Instance.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Instance source non trouvée'}, status=404)

    try:
        date_attributes = []

        # Utiliser l'API client directement pour récupérer un objet unique
        api = instance.get_api_client()

        if filter_type == 'event':
            # Pour les events, récupérer les dataElements de type date du programme
            # D'abord récupérer le programme avec ses stages
            response = api.get(
                f'programs/{program_uid}',
                params={
                    'fields': 'id,name,programStages[id,programStageDataElements[dataElement[id,name,displayName,valueType]]]',
                    'paging': 'false'
                }
            )
            response.raise_for_status()
            program = response.json()

            # Extraire les dataElements de type date
            seen_data_elements = set()
            if program and 'programStages' in program:
                for stage in program['programStages']:
                    if 'programStageDataElements' in stage:
                        for psde in stage['programStageDataElements']:
                            if 'dataElement' in psde:
                                de = psde['dataElement']
                                de_id = de.get('id')
                                value_type = de.get('valueType', '')

                                # Vérifier si c'est un type date et pas déjà ajouté
                                if de_id not in seen_data_elements and value_type in ['DATE', 'DATETIME', 'TIME']:
                                    date_attributes.append({
                                        'uid': de_id,
                                        'name': de.get('displayName') or de.get('name'),
                                        'valueType': value_type
                                    })
                                    seen_data_elements.add(de_id)

        else:  # tracker
            # Pour les tracker, récupérer les attributs de type date du programme
            response = api.get(
                f'programs/{program_uid}',
                params={
                    'fields': 'id,name,programTrackedEntityAttributes[trackedEntityAttribute[id,name,displayName,valueType]]',
                    'paging': 'false'
                }
            )
            response.raise_for_status()
            program = response.json()

            # Extraire les attributs de type date
            if program and 'programTrackedEntityAttributes' in program:
                for ptea in program['programTrackedEntityAttributes']:
                    if 'trackedEntityAttribute' in ptea:
                        attr = ptea['trackedEntityAttribute']
                        value_type = attr.get('valueType', '')

                        if value_type in ['DATE', 'DATETIME', 'TIME']:
                            date_attributes.append({
                                'uid': attr.get('id'),
                                'name': attr.get('displayName') or attr.get('name'),
                                'valueType': value_type
                            })

        return JsonResponse({
            'success': True,
            'attributes': date_attributes
        })

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des attributs de date: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors de la récupération des attributs: {str(e)}'
        }, status=500)
