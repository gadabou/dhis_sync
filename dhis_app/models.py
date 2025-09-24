from typing import Optional, Any, Dict
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import logging
from dhis2 import Api
from django.utils import timezone
from datetime import date



class DHIS2Instance(models.Model):
    name = models.CharField(max_length=100, unique=True)
    base_url = models.URLField()
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=255)
    version = models.CharField(max_length=20, blank=True, null=True, help_text="Version DHIS2 (ex: 2.38, 2.40)")
    is_source = models.BooleanField(default=False)
    is_destination = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, help_text="Instance active/inactive")
    connection_status = models.BooleanField(default=None, null=True, blank=True, help_text="Statut de connexion (True=connecté, False=déconnecté, None=non testé)")
    last_connection_test = models.DateTimeField(null=True, blank=True, help_text="Dernière vérification de connexion")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({'Source' if self.is_source else 'Destination'})"

    def clean(self):
        """Validation personnalisée"""
        super().clean()

        # Nettoyer l'URL pour éviter les double slashes
        if self.base_url:
            # Supprimer les slashes multiples à la fin
            self.base_url = self.base_url.rstrip('/')
            # S'assurer qu'il n'y a qu'un seul slash à la fin
            if not self.base_url.endswith('/'):
                self.base_url += '/'

        # Vérifier qu'au moins l'un des deux flags est activé
        if not self.is_source and not self.is_destination:
            raise ValidationError("Une instance doit être soit source, soit destination, soit les deux.")

    def get_api_client(self):
        """
        Crée et retourne un client API dhis2.py pour cette instance
        """
        try:
            # Nettoyer l'URL pour éviter les doubles slashes
            clean_url = self.base_url.rstrip('/') if self.base_url else ''

            print("base_url cleaned", clean_url)
            print("username", self.username)
            print("password", self.password)
            print("version", self.version)

            api = Api(
                server=clean_url,  # Passer l'URL sans slash final
                username=self.username,
                password=self.password
            )

            print("API", api.get_version())
            return api

        except Exception as e:
            raise ValidationError(f"Impossible de créer le client API: {str(e)}")

    def test_connection(self):
        """
        Test la connexion à l'instance DHIS2

        Returns:
            dict: Résultat du test avec statut et informations
        """
        try:
            api = self.get_api_client()

            # Test basique avec l'endpoint system/info
            response = api.get('system/info')

            if response.status_code == 200:
                info = response.json()
                return {
                    'success': True,
                    'message': 'Connexion réussie',
                    'dhis2_version': info.get('version'),
                    'system_name': info.get('systemName'),
                    'server_date': info.get('serverDate')
                }
            else:
                return {
                    'success': False,
                    'message': f'Erreur HTTP {response.status_code}: {response.text}'
                }

        except ImportError as e:
            return {
                'success': False,
                'message': str(e)
            }
        except ValidationError as e:
            return {
                'success': False,
                'message': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur de connexion: {str(e)}'
            }

    def get_metadata(self, resource, fields=None, paging=True, page_size=50):
        """
        Récupère les métadonnées depuis l'instance DHIS2

        Args:
            resource (str): Type de ressource (ex: 'dataElements', 'organisationUnits')
            fields (str): Champs à récupérer (ex: 'id,name,code')
            paging (bool): Utiliser la pagination
            page_size (int): Taille de page

        Returns:
            list: Liste des objets récupérés
        """
        try:
            api = self.get_api_client()

            params = {}
            if fields:
                params['fields'] = fields
            if paging:
                params['paging'] = 'true'
                params['pageSize'] = page_size
            else:
                params['paging'] = 'false'

            all_data = []
            page = 1

            while True:
                if paging:
                    params['page'] = page

                response = api.get(resource, params=params)
                response.raise_for_status()

                data = response.json()

                # Structure de réponse DHIS2
                if isinstance(data, dict) and resource in data:
                    items = data[resource]
                    all_data.extend(items)

                    # Vérifier s'il y a plus de pages
                    if paging and data.get('pager', {}).get('nextPage'):
                        page += 1
                    else:
                        break
                else:
                    # Réponse directe (pas de wrapper)
                    if isinstance(data, list):
                        all_data.extend(data)
                    break

            return all_data

        except Exception as e:
            logging.error(f"Erreur lors de la récupération de {resource}: {str(e)}")
            raise

    def post_metadata(self, resource, data, strategy='CREATE_AND_UPDATE'):
        """
        Envoie des métadonnées vers l'instance DHIS2.
        """
        try:
            api = self.get_api_client()

            # S’assurer que data est une liste
            items = data if isinstance(data, list) else [data]

            payload = {
                resource: items
            }

            # Options d’import en query params
            params = {
                'importStrategy': strategy,
                'atomicMode': 'NONE',          # pour permettre des succès partiels
                'mergeMode': 'MERGE',        # ou 'REPLACE'
                # 'preheatMode': 'REFERENCE',    # ou 'ALL'
                # 'skipValidation': 'false',
                # 'skipSharing': 'false',
            }
            response = api.post('metadata', data=payload, params=params)

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logging.error(f"Erreur lors de l'envoi de {resource}: {e}")
            raise

    def get_data_values(self, data_element, org_unit, period, category_option_combo=None, attribute_option_combo=None):
        """
        (Compat) Récupère UNE valeur agrégée.
        Redirige vers get_aggregate_value pour éviter les doublons.
        """
        return self.get_aggregate_value(
            dataElement=data_element,
            orgUnit=org_unit,
            period=period,
            categoryOptionCombo=category_option_combo,
            attributeOptionCombo=attribute_option_combo
        )

    def post_data_values(self, data_values):
        """
        Envoie des valeurs agrégées (lot) via /api/dataValueSets.
        """
        try:
            api = self.get_api_client()

            payload = {'dataValues': data_values}

            # Avec dhis2.Api, utiliser data= (et non json=)
            response = api.post('dataValueSets', data=payload)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logging.error(f"Erreur lors de l'envoi des données: {str(e)}")
            raise

    # ---- Nouveau : wrapper unifié + méthodes dédiées ----
    def get_data(self, data_type: str, **kwargs):
        """
        Routeur unifié:
          - 'aggregate' -> get_aggregate_value ( /api/dataValues )
          - 'event'     -> get_events         ( /api/events )
          - 'tracker'   -> get_tracked_entity_instances ( /api/trackedEntityInstances )
        """
        data_type = (data_type or "").strip().lower()
        if data_type == "aggregate":
            return self.get_aggregate_value(**kwargs)
        elif data_type == "event":
            return self.get_events(**kwargs)
        elif data_type == "tracker":
            return self.get_tracked_entity_instances(**kwargs)
        else:
            raise ValueError("data_type doit être 'aggregate', 'event' ou 'tracker'.")

    def get_aggregate_value(self, *, dataElement: Optional[str] = None, period: Optional[str] = None, orgUnit: Optional[str] = None, categoryOptionCombo: Optional[str] = None, attributeOptionCombo: Optional[str] = None, **aliases) -> Dict[str, Any]:
        """
        Récupère UNE valeur agrégée via /api/dataValues.
        Params requis: dataElement (de), period (pe), orgUnit (ou)
        Optionnels: categoryOptionCombo (co), attributeOptionCombo (ao)
        """
        api = self.get_api_client()

        # Alias (de/pe/ou/co/ao)
        dataElement = dataElement or aliases.pop("de", None)
        period = period or aliases.pop("pe", None)
        orgUnit = orgUnit or aliases.pop("ou", None)
        categoryOptionCombo = categoryOptionCombo or aliases.pop("co", None)
        attributeOptionCombo = attributeOptionCombo or aliases.pop("ao", None)

        self._require(dataElement, "dataElement (ou 'de')")
        self._require(period, "period (ou 'pe')")
        self._require(orgUnit, "orgUnit (ou 'ou')")

        params = {"dataElement": dataElement, "period": period, "orgUnit": orgUnit}
        if categoryOptionCombo:
            params["categoryOptionCombo"] = categoryOptionCombo
        if attributeOptionCombo:
            params["attributeOptionCombo"] = attributeOptionCombo

        r = api.get("dataValues", params=params)
        r.raise_for_status()
        return r.json()

    def get_events(self, *, program: str, orgUnit: str, startDate: str, endDate: str, programStage: Optional[str] = None, ouMode: str = "DESCENDANTS", status: Optional[str] = None, paging: str = "false", **extra,) -> Dict[str, Any]:
        """
        Récupère des events via /api/events.
        Requis: program, orgUnit, startDate, endDate
        """
        api = self.get_api_client()

        self._require(program, "program")
        self._require(orgUnit, "orgUnit")
        self._require(startDate, "startDate (YYYY-MM-DD)")
        self._require(endDate, "endDate (YYYY-MM-DD)")

        params = {
            "program": program,
            "orgUnit": orgUnit,
            "ouMode": ouMode,
            "startDate": startDate,
            "endDate": endDate,
            "paging": paging,
        }
        if programStage:
            params["programStage"] = programStage
        if status:
            params["status"] = status

        # Pass-through d'éventuels filtres DHIS2 supplémentaires
        params.update(extra or {})

        r = api.get("events", params=params)
        r.raise_for_status()
        return r.json()

    def get_tracked_entity_instances(self, *, program: str, orgUnit: str, ouMode: str = "DESCENDANTS", paging: str = "false", lastUpdatedStartDate: Optional[str] = None, lastUpdatedEndDate: Optional[str] = None, trackedEntityType: Optional[str] = None, **attribute_filters,) -> Dict[str, Any]:
        """
        Récupère des TEI via /api/trackedEntityInstances.
        Requis: program, orgUnit
        Optionnels: ouMode, paging, lastUpdatedStartDate/EndDate, trackedEntityType, attributs en filtres
        """
        api = self.get_api_client()

        self._require(program, "program")
        self._require(orgUnit, "orgUnit")

        params = {
            "program": program,
            "orgUnit": orgUnit,
            "ouMode": ouMode,
            "paging": paging,
        }
        if lastUpdatedStartDate:
            params["lastUpdatedStartDate"] = lastUpdatedStartDate
        if lastUpdatedEndDate:
            params["lastUpdatedEndDate"] = lastUpdatedEndDate
        if trackedEntityType:
            params["trackedEntityType"] = trackedEntityType

        # Pass-through (ex: attribute=uid:EQ:value, etc.)
        params.update(attribute_filters or {})

        r = api.get("trackedEntityInstances", params=params)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _require(value: Optional[str], label: str):
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"Paramètre requis manquant: {label}")

    def import_data_values(self, data_values, *, dry_run: bool = False, atomic_mode: str = "NONE", data_element_id_scheme: str = "UID", org_unit_id_scheme: str = "UID", data_set_id_scheme: str = "UID", data_value_set: dict | None = None,
    ):
        """
        Importe des données agrégées via /api/dataValueSets.

        Deux formats supportés:
          1) data_values = [{de, pe, ou, [co], [ao], value}, ...]
             -> payload: {"dataValues": [...]}

          2) data_value_set = {"dataSet": "...", "completeDate": "...",
                               "orgUnit": "...", "period": "...",
                               "dataValues": [...]}

        Params utiles:
          - dry_run: n’effectue pas l’écriture (diagnostic)
          - atomic_mode: 'ALL' | 'NONE'
          - *IdSchemes: 'UID' | 'CODE' (selon tes besoins)

        Retourne: import report (dict)
        """
        try:
            api = self.get_api_client()

            if data_value_set is not None:
                payload = data_value_set
            else:
                payload = {"dataValues": data_values}

            params = {
                "dryRun": str(dry_run).lower(),
                "atomicMode": atomic_mode,
                "dataElementIdScheme": data_element_id_scheme,
                "orgUnitIdScheme": org_unit_id_scheme,
                "dataSetIdScheme": data_set_id_scheme,
            }

            r = api.post("dataValueSets", data=payload, params=params)
            r.raise_for_status()
            return r.json()

        except Exception as e:
            logging.error(f"Erreur import dataValueSets: {e}")
            raise

    def import_events(
            self,
            events: list[dict] | dict,
            *,
            strategy: str = "CREATE_AND_UPDATE",
            atomic_mode: str = "NONE",
            async_import: bool = False,
            validation_mode: str | None = None,
            # Pass-through params supplémentaires: importMode, skipFirst, etc.
            **extra_params,
    ):
        """
        Importe des events via /api/events.

        - Accepte un événement unique (dict) ou un lot (list[dict]).
        - Si list -> payload {"events": [...]}
        - strategy: 'CREATE' | 'UPDATE' | 'CREATE_AND_UPDATE' | 'DELETE'
        - atomic_mode: 'ALL' | 'NONE'
        - async_import: True => import asynchrone (si dispo)
        - validation_mode: 'STRICT' | 'SOFT' (selon version)

        Retour: import report (dict)
        """
        try:
            api = self.get_api_client()

            if isinstance(events, dict) and "events" in events:
                payload = events
            elif isinstance(events, list):
                payload = {"events": events}
            elif isinstance(events, dict):
                payload = events  # unitaire (un objet event complet)
            else:
                raise ValueError("events doit être un dict (event) ou une list[dict].")

            params = {
                "importStrategy": strategy,
                "atomicMode": atomic_mode,
            }
            if async_import:
                params["async"] = "true"
            if validation_mode:
                params["validationMode"] = validation_mode

            params.update(extra_params or {})

            r = api.post("events", data=payload, params=params)
            r.raise_for_status()
            return r.json()

        except Exception as e:
            logging.error(f"Erreur import events: {e}")
            raise

    def import_tracker_bundle(
            self,
            *,
            tracked_entities: list[dict] | None = None,
            enrollments: list[dict] | None = None,
            events: list[dict] | None = None,
            relationships: list[dict] | None = None,
            strategy: str = "CREATE_AND_UPDATE",
            atomic_mode: str = "NONE",
            async_import: bool = False,
            validation_mode: str | None = None,
            # Pass-through params (importMode, preheatMode, skipRuleEngine, etc.)
            **extra_params,
    ):
        """
        Importe un bundle tracker (TEI/Enrollments/Events/Relationships).

        Endpoint recommandé (DHIS2 >= 2.39/2.40): POST /api/tracker
        Payload possible (toutes clés optionnelles, on n’envoie que ce qui est fourni):
        {
          "trackedEntities": [...],
          "enrollments": [...],
          "events": [...],
          "relationships": [...]
        }

        Params:
          - strategy: 'CREATE' | 'UPDATE' | 'CREATE_AND_UPDATE' | 'DELETE'
          - atomic_mode: 'ALL' | 'NONE'
          - async_import: True pour asynchrone (si dispo)
          - validation_mode: 'STRICT' | 'SOFT' (selon version)

        Fallback legacy (si /tracker non dispo):
          - Envoie séparément TEI (/trackedEntityInstances),
            enrollments (/enrollments) et events (/events).
            NB: ce fallback est minimaliste; adapte selon tes besoins métiers.
        """
        try:
            api = self.get_api_client()

            # Construire le bundle en ne gardant que les clés présentes
            bundle: dict = {}
            if tracked_entities:
                bundle["trackedEntities"] = tracked_entities
            if enrollments:
                bundle["enrollments"] = enrollments
            if events:
                bundle["events"] = events
            if relationships:
                bundle["relationships"] = relationships

            params = {
                "importStrategy": strategy,
                "atomicMode": atomic_mode,
            }
            if async_import:
                params["async"] = "true"
            if validation_mode:
                params["validationMode"] = validation_mode
            params.update(extra_params or {})

            # Essayer l’endpoint moderne /tracker
            try:
                r = api.post("tracker", data=bundle, params=params)
                r.raise_for_status()
                return r.json()
            except Exception as primary_err:
                # Fallback legacy minimal si /tracker indisponible
                logging.warning(f"/api/tracker indisponible, fallback legacy: {primary_err}")

                import_report = {"status": "OK", "reports": {}}

                # TEI (legacy)
                if tracked_entities:
                    try:
                        r_tei = api.post(
                            "trackedEntityInstances",
                            data={"trackedEntityInstances": tracked_entities},
                            params={"importStrategy": strategy, "atomicMode": atomic_mode},
                        )
                        r_tei.raise_for_status()
                        import_report["reports"]["trackedEntityInstances"] = r_tei.json()
                    except Exception as e:
                        import_report["status"] = "ERROR"
                        import_report["reports"]["trackedEntityInstances"] = {"error": str(e)}

                # Enrollments (legacy)
                if enrollments:
                    try:
                        r_enr = api.post(
                            "enrollments",
                            data={"enrollments": enrollments},
                            params={"importStrategy": strategy, "atomicMode": atomic_mode},
                        )
                        r_enr.raise_for_status()
                        import_report["reports"]["enrollments"] = r_enr.json()
                    except Exception as e:
                        import_report["status"] = "ERROR"
                        import_report["reports"]["enrollments"] = {"error": str(e)}

                # Events (legacy) — on réutilise la méthode events ci-dessus
                if events:
                    try:
                        rep_events = self.import_events(
                            events,
                            strategy=strategy,
                            atomic_mode=atomic_mode,
                            async_import=False,
                        )
                        import_report["reports"]["events"] = rep_events
                    except Exception as e:
                        import_report["status"] = "ERROR"
                        import_report["reports"]["events"] = {"error": str(e)}

                return import_report

        except Exception as e:
            logging.error(f"Erreur import tracker bundle: {e}")
            raise


class SyncConfiguration(models.Model):
    """
    Configuration de synchronisation DHIS2 avec architecture professionnelle

    Architecture recommandée:
    - metadata: Synchronisation des métadonnées uniquement (hebdomadaire)
    - all_data: Synchronisation de tous les types de données (quotidienne)
    - complete: Synchronisation complète avec orchestration des dépendances
    """

    SYNC_TYPES = [
        ('metadata', 'Métadonnées'),
        ('data', 'Données Agrégées'),
        ('events', 'Événements'),
        ('tracker', 'Données Tracker'),
        ('both', 'Métadonnées et Données Agrégées'),
        ('all_data', 'Toutes les Données'),  # 🆕 PROFESSIONNEL: aggregate + events + tracker
        ('complete', 'Synchronisation Complète'),  # 🆕 PROFESSIONNEL: metadata + all_data
    ]

    # Catégorisation professionnelle des types
    METADATA_SYNC_TYPES = ['metadata']
    DATA_SYNC_TYPES = ['data', 'events', 'tracker', 'all_data']
    COMPOSITE_SYNC_TYPES = ['both', 'complete']

    DATA_TYPES = [
        ('aggregate', 'Données Agrégées'),
        ('events', 'Événements'),
        ('tracker', 'Données Tracker'),
    ]

    IMPORT_STRATEGIES = [
        ('CREATE', 'Création seulement'),
        ('UPDATE', 'Mise à jour seulement'),
        ('CREATE_AND_UPDATE', 'Création et mise à jour'),
        ('DELETE', 'Suppression'),
    ]

    MERGE_MODES = [
        ('REPLACE', 'Remplacement complet'),
        ('MERGE', 'Fusion/mise à jour'),
    ]

    EXECUTION_MODES = [
        ('manual', 'Manuel'),
        ('automatic', 'Automatique'),
        ('scheduled', 'Planifié'),
    ]

    name = models.CharField(max_length=100)
    source_instance = models.ForeignKey(DHIS2Instance, on_delete=models.CASCADE, related_name='source_configs')
    destination_instance = models.ForeignKey(DHIS2Instance, on_delete=models.CASCADE, related_name='destination_configs')
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPES, default='metadata')

    # Nouveau champ pour spécifier le type de données (par défaut agrégé pour compatibilité)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES, default='aggregate',
                                 help_text="Type de données à synchroniser (applicable quand sync_type inclut 'data')")

    # Configuration de l'importation
    import_strategy = models.CharField(max_length=20, choices=IMPORT_STRATEGIES, default='CREATE_AND_UPDATE',
                                       help_text="Stratégie d'import lors de la synchronisation")
    merge_mode = models.CharField(max_length=10, choices=MERGE_MODES, default='MERGE',
                                  help_text="Mode de fusion lors de l'import (REPLACE ou MERGE)")

    # Configuration de l'exécution
    execution_mode = models.CharField(max_length=15, choices=EXECUTION_MODES, default='manual',
                                      help_text="Mode d'exécution de la synchronisation")

    # Configuration de pagination
    max_page_size = models.IntegerField(default=50, help_text="Taille maximale de page pour la récupération des données")
    supports_paging = models.BooleanField(default=True, help_text="Activer la pagination lors de la récupération")

    # Configuration de planification (pour execution_mode='scheduled')
    is_active = models.BooleanField(default=True)
    schedule_enabled = models.BooleanField(default=False, help_text="Activer la planification automatique")
    schedule_interval = models.IntegerField(default=60, help_text="Intervalle en minutes pour la planification")

    # Plage de données à synchroniser
    sync_start_date = models.DateField(null=True, blank=True, help_text="Date de début pour la synchronisation des données (laissez vide pour toutes les données)")
    sync_end_date = models.DateField(default=date.today, help_text="Date de fin pour la synchronisation des données (par défaut: aujourd'hui)")

    # Métadonnées
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_metadata_sync(self):
        """Indique si cette configuration synchronise les métadonnées"""
        return self.sync_type in self.METADATA_SYNC_TYPES or self.sync_type in self.COMPOSITE_SYNC_TYPES

    @property
    def is_data_sync(self):
        """Indique si cette configuration synchronise les données"""
        return self.sync_type in self.DATA_SYNC_TYPES or self.sync_type in self.COMPOSITE_SYNC_TYPES

    @property
    def is_composite_sync(self):
        """Indique si cette configuration est une synchronisation composite (multi-étapes)"""
        return self.sync_type in self.COMPOSITE_SYNC_TYPES

    @property
    def requires_metadata_dependency(self):
        """Indique si cette configuration nécessite les métadonnées comme prérequis"""
        return self.is_data_sync and not self.is_metadata_sync

    def get_data_types_for_all_data(self):
        """Retourne les types de données à synchroniser pour sync_type='all_data'"""
        if self.sync_type == 'all_data':
            return ['aggregate', 'events', 'tracker']
        elif self.sync_type == 'complete':
            return ['aggregate', 'events', 'tracker']
        elif self.sync_type == 'both':
            return [self.data_type or 'aggregate']
        else:
            return [self.data_type or 'aggregate']

    def get_orchestration_steps(self):
        """Retourne les étapes d'orchestration pour cette configuration"""
        steps = []

        if self.sync_type == 'complete':
            steps.append({'type': 'metadata', 'order': 1, 'critical': True})
            steps.append({'type': 'all_data', 'order': 2, 'critical': False, 'depends_on': 'metadata'})
        elif self.sync_type == 'both':
            steps.append({'type': 'metadata', 'order': 1, 'critical': True})
            steps.append({'type': 'data', 'data_type': self.data_type, 'order': 2, 'critical': False})
        elif self.sync_type == 'all_data':
            for i, data_type in enumerate(self.get_data_types_for_all_data()):
                steps.append({'type': 'data', 'data_type': data_type, 'order': i+1, 'critical': False})
        else:
            steps.append({'type': self.sync_type, 'order': 1, 'critical': True})

        return steps

    @property
    def is_manual_execution(self):
        """Indique si l'exécution est manuelle"""
        return self.execution_mode == 'manual'

    @property
    def is_automatic_execution(self):
        """Indique si l'exécution est automatique"""
        return self.execution_mode == 'automatic'

    @property
    def is_scheduled_execution(self):
        """Indique si l'exécution est planifiée"""
        return self.execution_mode == 'scheduled'

    def get_sync_params(self):
        """Retourne les paramètres de synchronisation configurés"""
        return {
            'import_strategy': self.import_strategy,
            'merge_mode': self.merge_mode,
            'max_page_size': self.max_page_size,
            'supports_paging': self.supports_paging,
            'execution_mode': self.execution_mode,
        }

    def clean(self):
        """Validation personnalisée"""
        super().clean()

        # Valider que la planification est cohérente
        if self.execution_mode == 'scheduled' and not self.schedule_enabled:
            raise ValidationError(
                "Pour un mode d'exécution planifié, 'schedule_enabled' doit être activé."
            )

        # Valider les paramètres de pagination
        if self.max_page_size <= 0:
            raise ValidationError("La taille de page doit être positive.")

        if self.max_page_size > 1000:
            raise ValidationError("La taille de page ne peut pas dépasser 1000 éléments.")

        # Valider les dates de synchronisation
        if self.sync_start_date and self.sync_end_date:
            if self.sync_start_date > self.sync_end_date:
                raise ValidationError("La date de début ne peut pas être postérieure à la date de fin.")

    @property
    def has_date_filter(self):
        """Indique si cette configuration utilise un filtre de dates"""
        return self.sync_start_date is not None or self.sync_end_date is not None


class MetadataType(models.Model):
    name = models.CharField(max_length=100)
    api_endpoint = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class SyncJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('running', 'En cours'),
        ('completed', 'Terminé'),
        ('completed_with_warnings', 'Terminé avec avertissements'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
        ('retrying', 'Nouvelle tentative'),
        ('failed_permanently', 'Échec définitif'),
    ]

    JOB_TYPES = [
        ('complete', 'Job Complet'),  # Job principal qui orchestre tout
        ('metadata', 'Métadonnées'),  # Job spécialisé métadonnées
        ('data', 'Données'),          # Job spécialisé données
        ('aggregate', 'Données Agrégées'),
        ('events', 'Événements'),
        ('tracker', 'Données Tracker'),
        ('all_data', 'Toutes Données'),
    ]

    sync_config = models.ForeignKey(SyncConfiguration, on_delete=models.CASCADE, related_name='jobs')
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, default='complete',
                                help_text="Type spécialisé de ce job")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress = models.IntegerField(default=0)
    total_items = models.IntegerField(default=0)
    processed_items = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    log_message = models.TextField(blank=True)

    # Champs pour la gestion des retries
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True, null=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    parent_job = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='retry_jobs')
    is_retry = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Job {self.id} - {self.sync_config.name} ({self.get_job_type_display()}) - {self.status}"

    @property
    def display_name(self):
        """Nom d'affichage du job avec type"""
        return f"{self.sync_config.name} - {self.get_job_type_display()}"

    @property
    def progress_percentage(self):
        if self.total_items == 0:
            return 0
        return int((self.processed_items / self.total_items) * 100)

    @property
    def is_composite_job(self):
        """Indique si ce job est un job composite (contient des sous-jobs)"""
        return self.sub_jobs.exists()

    @property
    def is_sub_job(self):
        """Indique si ce job est un sous-job d'un job parent"""
        return self.parent_job is not None

    def get_aggregate_stats(self):
        """Retourne les statistiques agrégées incluant les sous-jobs"""
        if not self.is_composite_job:
            return {
                'total_items': self.total_items,
                'processed_items': self.processed_items,
                'success_count': self.success_count,
                'error_count': self.error_count,
                'warning_count': self.warning_count,
                'progress': self.progress
            }

        # Agréger les stats des sous-jobs
        sub_jobs = self.sub_jobs.all()
        total_items = sum(job.total_items for job in sub_jobs)
        processed_items = sum(job.processed_items for job in sub_jobs)
        success_count = sum(job.success_count for job in sub_jobs)
        error_count = sum(job.error_count for job in sub_jobs)
        warning_count = sum(job.warning_count for job in sub_jobs)

        progress = int((processed_items / total_items) * 100) if total_items > 0 else 0

        return {
            'total_items': total_items,
            'processed_items': processed_items,
            'success_count': success_count,
            'error_count': error_count,
            'warning_count': warning_count,
            'progress': progress
        }

    def can_retry(self):
        """Vérifie si ce job peut être relancé"""
        return (
                self.status in ['failed'] and
                self.retry_count < self.max_retries and
                not self.is_retry
        )

    def should_retry_now(self):
        """Vérifie si le moment est venu pour un retry"""
        if not self.can_retry():
            return False
        if self.next_retry_at is None:
            return True
        return timezone.now() >= self.next_retry_at

    def calculate_retry_delay(self):
        """Calcule le délai avant le prochain retry (backoff exponentiel)"""
        from datetime import timedelta
        base_delay = 60  # 1 minute
        delay_seconds = base_delay * (2 ** self.retry_count)  # 1min, 2min, 4min, 8min...
        return timedelta(seconds=min(delay_seconds, 3600))  # Max 1 heure

    def schedule_retry(self):
        """Programme un retry pour ce job"""
        if self.can_retry():
            from django.utils import timezone
            delay = self.calculate_retry_delay()
            self.next_retry_at = timezone.now() + delay
            self.status = 'retrying'
            self.save()
            return True
        return False


class DHIS2Entity(models.Model):
    """Modèle pour gérer tous les objets DHIS2 avec leurs dépendances et ordre d'import"""

    ENTITY_TYPES = [
        # NIVEAU 1: Entités de base (aucune dépendance)
        ('periodTypes', 'Period Types'),
        ('userRoles', 'User Roles'),
        ('users', 'Users'),
        ('userGroups', 'User Groups'),

        # NIVEAU 2: Options et catégories de base
        ('categoryOptions', 'Category Options'),

        # NIVEAU 3: Catégories (dépendent des categoryOptions)
        ('categories', 'Categories'),

        # NIVEAU 4: Combinaisons de catégories (dépendent des categories)
        ('categoryCombos', 'Category Combos'),
        ('categoryOptionCombos', 'Category Option Combos'),

        # NIVEAU 5: Types spécialisés
        ('indicatorTypes', 'Indicator Types'),

        # NIVEAU 6: Organisation - niveaux d'abord
        ('organisationUnitLevels', 'Organisation Unit Levels'),

        # NIVEAU 7: Unités d'organisation (dépendent des niveaux)
        ('organisationUnits', 'Organisation Units'),

        # NIVEAU 8: Groupes d'unités (dépendent des unités)
        ('organisationUnitGroups', 'Organisation Unit Groups'),
        ('organisationUnitGroupSets', 'Organisation Unit Group Sets'),

        # NIVEAU 9: Ensembles d'options
        ('optionSets', 'Option Sets'),

        # NIVEAU 10: Options (dépendent des optionSets)
        ('options', 'Options'),

        # NIVEAU 11: Groupes d'éléments de données (avant les éléments)
        ('dataElementGroups', 'Data Element Groups'),
        ('dataElementGroupSets', 'Data Element Group Sets'),

        # NIVEAU 12: Éléments de données (dépendent de categoryCombos, optionSets)
        ('dataElements', 'Data Elements'),
        ('dataElementOperands', 'Data Element Operands'),

        # NIVEAU 13: Groupes d'indicateurs (avant les indicateurs)
        ('indicatorGroups', 'Indicator Groups'),
        ('indicatorGroupSets', 'Indicator Group Sets'),

        # NIVEAU 14: Indicateurs (dépendent des indicatorTypes et dataElements)
        ('indicators', 'Indicators'),

        # NIVEAU 15: Ensembles de données (dépendent des dataElements et organisationUnits)
        ('dataSets', 'Data Sets'),
        ('dataSetElements', 'Data Set Elements'),  # Relations dataSet ↔ dataElement
        ('dataInputPeriods', 'Data Input Periods'),

        # NIVEAU 16: Entités suivies - types d'abord
        ('trackedEntityTypes', 'Tracked Entity Types'),

        # NIVEAU 17: Attributs d'entités suivies
        ('trackedEntityAttributes', 'Tracked Entity Attributes'),
        ('trackedEntityAttributeGroups', 'Tracked Entity Attribute Groups'),

        # NIVEAU 18: Instances d'entités suivies
        ('trackedEntityInstances', 'Tracked Entity Instances'),

        # NIVEAU 19: Programmes (dépendent de trackedEntityTypes, organisationUnits)
        ('programs', 'Programs'),

        # NIVEAU 20: Étapes de programmes (dépendent des programmes)
        ('programStages', 'Program Stages'),

        # NIVEAU 21: Éléments de données de programmes
        ('programStageDataElements', 'Program Stage Data Elements'),
        ('programDataElements', 'Program Data Elements'),

        # NIVEAU 22: Indicateurs de programmes
        ('programIndicators', 'Program Indicators'),

        # NIVEAU 23: Règles de programmes (dépendent des programmes)
        ('programRules', 'Program Rules'),

        # NIVEAU 24: Variables de règles (dépendent des programmes)
        ('programRuleVariables', 'Program Rule Variables'),

        # NIVEAU 25: Actions de règles (dépendent des règles)
        ('programRuleActions', 'Program Rule Actions'),

        # NIVEAU 26: Validation - règles d'abord
        ('validationRules', 'Validation Rules'),

        # NIVEAU 27: Groupes de validation (dépendent des règles)
        ('validationRuleGroups', 'Validation Rule Groups'),

        # NIVEAU 28: Prédicteurs
        ('predictors', 'Predictors'),
        ('predictorGroups', 'Predictor Groups'),

        # NIVEAU 29: Légendes et ensembles
        ('legendSets', 'Legend Sets'),
        ('legends', 'Legends'),

        # NIVEAU 30: Visualisation et analyses
        ('charts', 'Charts'),
        ('reports', 'Reports'),
        ('reportTables', 'Report Tables'),
        ('maps', 'Maps'),
        ('visualizations', 'Visualizations'),
        ('eventCharts', 'Event Charts'),
        ('eventReports', 'Event Reports'),
        ('dashboards', 'Dashboards'),

        # NIVEAU 31: Autres entités transversales
        ('attributes', 'Attributes'),
        ('constants', 'Constants'),
        ('documents', 'Documents'),
        ('interpretations', 'Interpretations'),
        ('messageConversations', 'Message Conversations'),
    ]

    IMPORT_ORDER = {
        # User
        'userGroups': 1,
        'userRoles': 2,
        'users': 3,

        # Transversaux utiles tôt
        'attributes': 4,
        'constants': 5,

        # Organisation
        'organisationUnitLevels': 10,
        'organisationUnits': 11,
        'organisationUnitGroups': 12,
        'organisationUnitGroupSets': 13,

        # Catégories
        'categoryOptions': 20,
        'categories': 21,
        'categoryCombos': 22,
        'categoryOptionGroups': 23,
        'categoryOptionGroupSets': 24,

        # Options
        'optionSets': 30,
        'options': 31,

        # Légendes (si séparées)
        'legends': 39,
        'legendSets': 40,

        # Data Elements & Groups (éléments avant groupes)
        'dataElements': 50,
        'dataElementGroups': 51,
        'dataElementGroupSets': 52,

        # Validation
        'validationRules': 60,
        'validationRuleGroups': 61,

        # Data Sets (ensembles avant liaisons/periods)
        'dataSets': 70,
        'dataSetElements': 71,
        'dataInputPeriods': 72,

        # Indicators & Groups (indicateurs avant groupes)
        'indicatorTypes': 80,
        'indicators': 81,
        'indicatorGroups': 82,
        'indicatorGroupSets': 83,

        # Tracker
        'trackedEntityTypes': 90,
        'trackedEntityAttributes': 91,
        'trackedEntityAttributeGroups': 92,
        'programs': 100,
        'programStages': 101,
        'programStageDataElements': 102,
        'programIndicators': 103,
        'programRuleVariables': 104,
        'programRules': 105,
        'programRuleActions': 106,
        'relationshipTypes': 107,
        'notificationTemplates': 108,

        # Analytique & Présentation
        'reportTables': 120,
        'eventReports': 121,
        'visualizations': 122,
        'charts': 123,
        'maps': 124,
        'dashboards': 125,

        # Prédicteurs
        'predictors': 130,
        'predictorGroups': 131,

        # Divers
        'documents': 140,
        'interpretations': 141,
        'messageConversations': 142,
    }


    # Informations de l'objet DHIS2
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPES)
    dhis2_uid = models.CharField(max_length=11, help_text="UID DHIS2 de l'objet")
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    short_name = models.CharField(max_length=50, blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)

    # Configuration de synchronisation
    sync_config = models.ForeignKey(SyncConfiguration, on_delete=models.CASCADE, related_name='entities')
    is_selected = models.BooleanField(default=True, help_text="Inclure dans la synchronisation")
    import_order = models.IntegerField(help_text="Ordre d'import basé sur les dépendances")

    # Métadonnées de synchronisation
    last_synchronized = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=20, choices=[
        ('pending', 'En attente'),
        ('success', 'Synchronisé'),
        ('failed', 'Échec'),
        ('skipped', 'Ignoré'),
    ], default='pending')
    sync_error_message = models.TextField(blank=True, null=True)

    # Informations spécifiques aux versions pour la synchronisation
    source_version_info = models.ForeignKey( 'DHIS2EntityVersion', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_entities', help_text="Informations de version pour l'instance source")
    destination_version_info = models.ForeignKey('DHIS2EntityVersion', on_delete=models.SET_NULL, null=True, blank=True, related_name='destination_entities', help_text="Informations de version pour l'instance destination")

    # Mapping des champs entre versions différentes
    field_mapping = models.JSONField(default=dict, blank=True, help_text="Mapping des champs entre les versions source et destination (source_field: destination_field)")

    # Transformations de données nécessaires
    data_transformations = models.JSONField(default=dict, blank=True, help_text="Transformations de données nécessaires lors de la synchronisation")

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['sync_config', 'entity_type', 'dhis2_uid']]
        indexes = [
            models.Index(fields=['sync_config', 'entity_type']),
            models.Index(fields=['import_order']),
            models.Index(fields=['is_selected']),
        ]
        ordering = ['import_order', 'name']

    def save(self, *args, **kwargs):
        # Auto-définir l'ordre d'import basé sur le type
        if not self.import_order:
            self.import_order = self.IMPORT_ORDER.get(self.entity_type, 999)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_entity_type_display()}: {self.name} ({self.dhis2_uid})"

    @property
    def has_dependencies(self):
        """Vérifie si ce type d'entité a des dépendances"""
        dependencies = self.get_dependencies()
        return len(dependencies) > 0

    def get_dependencies(self):
        """Retourne la liste des types d'entités dont dépend ce type"""
        dependency_map = {
            # Catégories
            'categories': ['categoryOptions'],
            'categoryCombos': ['categories'],
            'categoryOptionCombos': ['categoryCombos', 'categories'],

            # Organisation
            'organisationUnits': ['organisationUnitLevels'],
            'organisationUnitGroups': ['organisationUnits'],
            'organisationUnitGroupSets': ['organisationUnitGroups'],

            # Options
            'options': ['optionSets'],

            # Éléments de données
            'dataElements': ['categoryCombos', 'optionSets', 'dataElementGroups'],
            'dataElementOperands': ['dataElements'],
            'dataElementGroupSets': ['dataElementGroups'],

            # Indicateurs
            'indicators': ['indicatorTypes', 'dataElements', 'indicatorGroups'],
            'indicatorGroupSets': ['indicatorGroups'],

            # Ensembles de données
            'dataSets': ['dataElements', 'categoryCombos', 'organisationUnits'],
            'dataSetElements': ['dataSets', 'dataElements'],  # Relations dataSet ↔ dataElement
            'dataInputPeriods': ['dataSets'],

            # Tracker
            'trackedEntityAttributes': ['trackedEntityTypes', 'optionSets'],
            'trackedEntityAttributeGroups': ['trackedEntityAttributes'],
            'trackedEntityInstances': ['trackedEntityTypes', 'trackedEntityAttributes'],
            'programs': ['trackedEntityTypes', 'organisationUnits', 'trackedEntityAttributes'],
            'programStages': ['programs'],
            'programStageDataElements': ['programStages', 'dataElements'],
            'programIndicators': ['programs', 'dataElements'],
            'programRules': ['programs'],
            'programRuleVariables': ['programs'],
            'programRuleActions': ['programRules'],

            # Validation
            'validationRules': ['dataElements', 'organisationUnits'],
            'validationRuleGroups': ['validationRules'],

            # Prédicteurs
            'predictors': ['dataElements', 'organisationUnits'],
            'predictorGroups': ['predictors'],

            # Légendes
            'legends': ['legendSets'],

            # Visualisations
            'visualizations': ['dataElements', 'indicators', 'organisationUnits'],
            'charts': ['dataElements', 'indicators', 'organisationUnits'],
            'reportTables': ['dataElements', 'indicators', 'organisationUnits'],
            'maps': ['dataElements', 'indicators', 'organisationUnits'],
            'eventCharts': ['programs', 'dataElements'],
            'eventReports': ['programs', 'dataElements'],
            'dashboards': ['visualizations', 'charts', 'reportTables', 'maps'],
        }
        return dependency_map.get(self.entity_type, [])

    @classmethod
    def get_entities_by_order(cls, sync_config):
        """Retourne les entités dans l'ordre d'import correct"""
        return cls.objects.filter(
            sync_config=sync_config,
            is_selected=True
        ).order_by('import_order', 'name')

    @classmethod
    def get_entities_by_type(cls, sync_config, entity_type):
        """Retourne les entités d'un type spécifique"""
        return cls.objects.filter(
            sync_config=sync_config,
            entity_type=entity_type,
            is_selected=True
        ).order_by('name')

    @property
    def has_version_differences(self):
        """Vérifie si les versions source et destination sont différentes"""
        if not self.source_version_info or not self.destination_version_info:
            return False
        return self.source_version_info.dhis2_version != self.destination_version_info.dhis2_version

    def get_mapped_field(self, source_field):
        """Retourne le champ destination mappé pour un champ source"""
        return self.field_mapping.get(source_field, source_field)

    def update_version_info(self):
        """Met à jour automatiquement les informations de version basées sur la configuration de sync"""
        source_version = self.sync_config.source_instance.version
        dest_version = self.sync_config.destination_instance.version

        if source_version:
            self.source_version_info = DHIS2EntityVersion.get_version_info(source_version, self.entity_type)

        if dest_version:
            self.destination_version_info = DHIS2EntityVersion.get_version_info(dest_version, self.entity_type)

        self.save()

    def generate_field_mapping(self):
        """Génère automatiquement le mapping des champs entre versions"""
        if not self.has_version_differences:
            return {}

        source_fields = set(self.source_version_info.get_effective_fields()) if self.source_version_info else set()
        dest_fields = set(self.destination_version_info.get_effective_fields()) if self.destination_version_info else set()

        # Mapping automatique pour les champs communs
        common_fields = source_fields.intersection(dest_fields)
        mapping = {field: field for field in common_fields}

        # Gérer les champs dépréciés/nouveaux
        if self.source_version_info and self.destination_version_info:
            deprecated_in_dest = set(self.destination_version_info.deprecated_fields)
            new_in_dest = set(self.destination_version_info.new_fields)

            # Ajouter des mappings suggérés pour les transformations courantes
            for deprecated_field in deprecated_in_dest:
                if deprecated_field in source_fields:
                    # Trouver un champ de remplacement potentiel
                    for new_field in new_in_dest:
                        if self._fields_are_similar(deprecated_field, new_field):
                            mapping[deprecated_field] = new_field
                            break

        return mapping

    def _fields_are_similar(self, field1, field2):
        """Heuristique simple pour déterminer si deux champs sont similaires"""
        # Exemples de similarités courantes dans DHIS2
        similarity_pairs = [
            ('code', 'shortName'),
            ('name', 'displayName'),
            ('organisationUnit', 'organisationUnits'),
        ]

        for pair in similarity_pairs:
            if (field1 in pair and field2 in pair) or (field2 in pair and field1 in pair):
                return True

        return False


class DHIS2EntityVersion(models.Model):
    """Modèle pour stocker les informations spécifiques à une version DHIS2 pour chaque type d'entité"""

    dhis2_version = models.CharField(max_length=20, help_text="Version DHIS2 (ex: 2.38, 2.40)")
    entity_type = models.CharField(max_length=50, choices=DHIS2Entity.ENTITY_TYPES)

    # Informations API spécifiques à cette version
    api_endpoint = models.CharField(max_length=100, help_text="Endpoint API pour cette entité dans cette version")
    api_path = models.CharField(max_length=200, blank=True, null=True, help_text="Chemin API complet si différent de l'endpoint")

    # Configuration des champs supportés dans cette version
    supported_fields = models.JSONField(default=list, help_text="Liste des champs supportés pour cette entité dans cette version")
    required_fields = models.JSONField(default=list, help_text="Liste des champs obligatoires pour cette entité dans cette version")
    deprecated_fields = models.JSONField(default=list,help_text="Liste des champs dépréciés dans cette version")
    new_fields = models.JSONField(default=list, help_text="Liste des nouveaux champs introduits dans cette version")

    # Configuration de pagination et limites
    max_page_size = models.IntegerField(default=50, help_text="Taille maximale de page pour cette entité")
    supports_paging = models.BooleanField(default=True, help_text="Cette entité supporte-t-elle la pagination")

    # Configuration de l'import/export
    supports_bulk_import = models.BooleanField(default=True, help_text="Support de l'import en lot")
    supports_upsert = models.BooleanField(default=True, help_text="Support de l'upsert (insertion/mise à jour)")
    import_strategy = models.CharField(max_length=20,
        choices=[
            ('CREATE', 'Création seulement'),
            ('UPDATE', 'Mise à jour seulement'),
            ('CREATE_AND_UPDATE', 'Création et mise à jour'),
            ('DELETE', 'Suppression'),
        ], default='CREATE_AND_UPDATE'
    )

    # Contraintes et validations spécifiques
    validation_rules = models.JSONField(default=dict, blank=True, help_text="Règles de validation spécifiques à cette version"
    )

    # Métadonnées
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Notes sur les particularités de cette version")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['dhis2_version', 'entity_type']]
        indexes = [
            models.Index(fields=['dhis2_version', 'entity_type']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['dhis2_version', 'entity_type']

    def __str__(self):
        return f"{self.dhis2_version} - {self.get_entity_type_display()}"

    @classmethod
    def get_version_info(cls, version, entity_type):
        """Récupère les informations de version pour une entité donnée"""
        try:
            return cls.objects.get(dhis2_version=version, entity_type=entity_type, is_active=True)
        except cls.DoesNotExist:
            return None

    def get_effective_fields(self):
        """Retourne les champs effectifs (supportés - dépréciés)"""
        supported = set(self.supported_fields)
        deprecated = set(self.deprecated_fields)
        return list(supported - deprecated)


    def is_field_supported(self, field_name):
        """Vérifie si un champ est supporté dans cette version"""
        return field_name in self.supported_fields and field_name not in self.deprecated_fields


class AutoSyncSettings(models.Model):
    """Configuration pour la synchronisation automatique"""

    sync_config = models.OneToOneField(SyncConfiguration, on_delete=models.CASCADE, related_name='auto_sync_settings')
    is_enabled = models.BooleanField(default=False, help_text="Activer la synchronisation automatique")
    check_interval = models.IntegerField(default=300, help_text="Intervalle de vérification en secondes (min: 60s)")
    immediate_sync = models.BooleanField(default=True, help_text="Déclencher la synchronisation immédiatement après détection")
    delay_before_sync = models.IntegerField(default=30, help_text="Délai avant synchronisation en secondes")

    # Monitoring haute fréquence pour déclenchement rapide
    high_frequency_mode = models.BooleanField(default=False, help_text="Activer le monitoring haute fréquence (30s)")
    high_frequency_interval = models.IntegerField(default=30, help_text="Intervalle en haute fréquence (secondes)")
    high_frequency_resources = models.JSONField(
        default=list,
        blank=True,
        help_text="Ressources spécifiques en haute fréquence (organisationUnits, dataElements, etc.)"
    )

    # Ressources à surveiller
    monitor_metadata = models.BooleanField(default=True)
    monitor_data_values = models.BooleanField(default=True)

    # Filtrages spécifiques
    metadata_resources = models.JSONField(default=list, blank=True, help_text="Liste des ressources métadonnées à surveiller")
    exclude_resources = models.JSONField(default=list, blank=True, help_text="Ressources à exclure de la surveillance")

    # Limites de sécurité
    max_sync_per_hour = models.IntegerField(default=10, help_text="Nombre maximum de synchronisations par heure")
    cooldown_after_error = models.IntegerField(default=1800, help_text="Délai d'attente après erreur en secondes")

    # Notifications
    notify_on_change = models.BooleanField(default=True)
    notify_on_sync_start = models.BooleanField(default=False)
    notify_on_sync_complete = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AutoSync {self.sync_config.name} ({'Actif' if self.is_enabled else 'Inactif'})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.check_interval < 60:
            raise ValidationError("L'intervalle de vérification doit être d'au moins 60 secondes")

