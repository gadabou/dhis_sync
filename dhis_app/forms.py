from django import forms
from django.core.exceptions import ValidationError
from .models import DHIS2Instance, SyncConfiguration


class DHIS2InstanceForm(forms.ModelForm):
    """Formulaire pour créer/modifier une instance DHIS2"""

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe',
            'autocomplete': 'new-password'
        }),
        help_text="Mot de passe pour l'authentification DHIS2"
    )

    class Meta:
        model = DHIS2Instance
        fields = ['name', 'base_url', 'username', 'password', 'version', 'is_source', 'is_destination']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'instance'
            }),
            'base_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://dhis2.example.com'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom d\'utilisateur DHIS2'
            }),
            'version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '2.40 (optionnel)'
            }),
            'is_source': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_destination': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        help_texts = {
            'name': 'Nom descriptif pour identifier cette instance',
            'base_url': 'URL complète de l\'instance DHIS2 (avec https://)',
            'username': 'Nom d\'utilisateur avec les permissions appropriées',
            'version': 'Version DHIS2 (ex: 2.38, 2.40) - laissez vide pour détection automatique',
            'is_source': 'Cette instance peut être utilisée comme source de données',
            'is_destination': 'Cette instance peut être utilisée comme destination'
        }

    def clean(self):
        cleaned_data = super().clean()
        is_source = cleaned_data.get('is_source')
        is_destination = cleaned_data.get('is_destination')

        if not is_source and not is_destination:
            raise ValidationError("Une instance doit être soit source, soit destination, soit les deux.")

        return cleaned_data

    def clean_base_url(self):
        base_url = self.cleaned_data.get('base_url')
        if base_url:
            if not base_url.startswith(('http://', 'https://')):
                raise ValidationError("L'URL doit commencer par http:// ou https://")

            if not base_url.endswith('/'):
                base_url += '/'

        return base_url


class SyncConfigurationForm(forms.ModelForm):
    """Formulaire pour créer/modifier une configuration de synchronisation"""

    class Meta:
        model = SyncConfiguration
        fields = [
            'name', 'source_instance', 'destination_instance', 'sync_type', 'data_type',
            'import_strategy', 'merge_mode', 'execution_mode', 'max_page_size', 'supports_paging',
            'is_active', 'schedule_enabled', 'schedule_interval', 'sync_start_date', 'sync_end_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de la configuration'
            }),
            'source_instance': forms.Select(attrs={
                'class': 'form-select'
            }),
            'destination_instance': forms.Select(attrs={
                'class': 'form-select'
            }),
            'sync_type': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'updateDataTypeVisibility()'
            }),
            'data_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'import_strategy': forms.Select(attrs={
                'class': 'form-select'
            }),
            'merge_mode': forms.Select(attrs={
                'class': 'form-select'
            }),
            'execution_mode': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'updateScheduleVisibility()'
            }),
            'max_page_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '1000'
            }),
            'supports_paging': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'schedule_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'onchange': 'updateScheduleInterval()'
            }),
            'schedule_interval': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'sync_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'sync_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
        help_texts = {
            'name': 'Nom descriptif pour cette configuration',
            'source_instance': 'Instance DHIS2 source (doit être marquée comme source)',
            'destination_instance': 'Instance DHIS2 destination (doit être marquée comme destination)',
            'sync_type': 'Type de données à synchroniser',
            'data_type': 'Type spécifique de données (applicable selon le type de sync)',
            'import_strategy': 'Stratégie d\'import lors de la synchronisation',
            'merge_mode': 'Mode de fusion des données existantes',
            'execution_mode': 'Mode d\'exécution de la synchronisation',
            'max_page_size': 'Taille maximale des pages lors de la récupération (1-1000)',
            'supports_paging': 'Utiliser la pagination pour optimiser les performances',
            'is_active': 'Configuration active et utilisable',
            'schedule_enabled': 'Activer la planification automatique',
            'schedule_interval': 'Intervalle entre les synchronisations automatiques (en minutes)',
            'sync_start_date': 'Date de début pour filtrer les données (optionnel)',
            'sync_end_date': 'Date de fin pour filtrer les données'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrer les instances source et destination
        source_instances = DHIS2Instance.objects.filter(is_source=True)
        dest_instances = DHIS2Instance.objects.filter(is_destination=True)

        self.fields['source_instance'].queryset = source_instances
        self.fields['destination_instance'].queryset = dest_instances

        # Ajouter des choix vides si aucune instance disponible
        if not source_instances.exists():
            self.fields['source_instance'].empty_label = "Aucune instance source disponible"
        if not dest_instances.exists():
            self.fields['destination_instance'].empty_label = "Aucune instance destination disponible"

    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('source_instance')
        destination = cleaned_data.get('destination_instance')
        execution_mode = cleaned_data.get('execution_mode')
        schedule_enabled = cleaned_data.get('schedule_enabled')
        sync_start_date = cleaned_data.get('sync_start_date')
        sync_end_date = cleaned_data.get('sync_end_date')

        # Vérifier que source et destination sont différentes
        if source and destination and source.id == destination.id:
            raise ValidationError("L'instance source et destination doivent être différentes.")

        # Vérifier la cohérence de la planification
        if execution_mode == 'scheduled' and not schedule_enabled:
            raise ValidationError({
                'schedule_enabled': "Pour un mode d'exécution planifié, la planification doit être activée."
            })

        # Vérifier les dates
        if sync_start_date and sync_end_date and sync_start_date > sync_end_date:
            raise ValidationError({
                'sync_start_date': "La date de début ne peut pas être postérieure à la date de fin."
            })

        return cleaned_data

    def clean_max_page_size(self):
        max_page_size = self.cleaned_data.get('max_page_size')
        if max_page_size:
            if max_page_size < 1:
                raise ValidationError("La taille de page doit être au moins 1.")
            if max_page_size > 1000:
                raise ValidationError("La taille de page ne peut pas dépasser 1000.")
        return max_page_size

    def clean_schedule_interval(self):
        schedule_interval = self.cleaned_data.get('schedule_interval')
        schedule_enabled = self.cleaned_data.get('schedule_enabled')

        if schedule_enabled and schedule_interval:
            if schedule_interval < 1:
                raise ValidationError("L'intervalle doit être au moins 1 minute.")

        return schedule_interval


class ConfigurationFilterForm(forms.Form):
    """Formulaire pour filtrer les configurations"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher...'
        })
    )

    sync_type = forms.ChoiceField(
        choices=[('', 'Tous les types')] + SyncConfiguration.SYNC_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    is_active = forms.ChoiceField(
        choices=[
            ('', 'Tous les statuts'),
            ('true', 'Actif'),
            ('false', 'Inactif')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )