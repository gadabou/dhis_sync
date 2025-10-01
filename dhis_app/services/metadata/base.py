"""
Service de base pour la synchronisation des métadonnées DHIS2
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone
from ...models import DHIS2Instance, SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class MetadataServiceError(Exception):
    """Exception personnalisée pour les services de métadonnées"""
    pass


class BaseMetadataService:
    """Service de base pour la synchronisation des métadonnées"""

    # Configuration des familles de métadonnées selon l'ordre DHIS2
    METADATA_FAMILIES_CONFIG = {
        'users': {
            'resources': ['userGroups', 'userRoles', 'users'],
            'description': 'Utilisateurs, rôles et groupes',
            'priority': 1,
            'dependencies': []
        },
        'organisation': {
            'resources': ['organisationUnitLevels', 'organisationUnits', 'organisationUnitGroups', 'organisationUnitGroupSets'],
            'description': 'Structure organisationnelle complète',
            'priority': 2,
            'dependencies': ['users']
        },
        'categories': {
            'resources': ['categoryOptions', 'categories', 'categoryCombos', 'categoryOptionGroups', 'categoryOptionGroupSets'],
            'description': 'Système de catégories DHIS2',
            'priority': 3,
            'dependencies': ['organisation']
        },
        'options': {
            'resources': ['options', 'optionSets'],
            'description': 'Options et ensembles d\'options',
            'priority': 4,
            'dependencies': []
        },
        'system': {
            'resources': ['attributes', 'constants'],
            'description': 'Configuration système de base',
            'priority': 5,
            'dependencies': []
        },
        'data_elements': {
            'resources': ['dataElements', 'dataElementGroups', 'dataElementGroupSets'],
            'description': 'Éléments de données et groupements',
            'priority': 6,
            'dependencies': ['system', 'categories', 'options']
        },
        'indicators': {
            'resources': ['indicatorTypes', 'indicators', 'indicatorGroups', 'indicatorGroupSets'],
            'description': 'Indicateurs et types d\'indicateurs',
            'priority': 7,
            'dependencies': ['data_elements']
        },
        'data_sets': {
            'resources': ['dataEntryForms', 'dataSets', 'dataSetElements', 'dataInputPeriods', 'dataSetNotificationTemplates'],
            'description': 'Formulaires et ensembles de données',
            'priority': 8,
            'dependencies': ['data_elements', 'categories']
        },
        'tracker': {
            'resources': ['trackedEntityTypes', 'trackedEntityAttributes', 'trackedEntityAttributeGroups'],
            'description': 'Entités suivies et attributs',
            'priority': 9,
            'dependencies': ['options', 'organisation']
        },
        'system_misc': {
            'resources': ['relationshipTypes'],
            'description': 'Types de relations',
            'priority': 10,
            'dependencies': []
        },
        'programs': {
            'resources': ['programs', 'programStageSections', 'programStages', 'programStageDataElements', 'programRuleActions', 'programIndicators', 'programRuleVariables', 'programRules', 'programNotificationTemplates'],
            'description': 'Programmes de suivi et règles',
            'priority': 11,
            'dependencies': ['tracker', 'data_elements', 'categories', 'system_misc']
        },
        'validation': {
            'resources': ['validationRules', 'validationRuleGroups', 'validationNotificationTemplates'],
            'description': 'Règles de validation des données',
            'priority': 12,
            'dependencies': ['data_elements', 'programs']
        },
        'predictors': {
            'resources': ['predictors', 'predictorGroups'],
            'description': 'Prédicteurs et groupes',
            'priority': 13,
            'dependencies': ['data_elements', 'indicators']
        },
        'legends': {
            'resources': ['legends', 'legendSets'],
            'description': 'Légendes pour cartes et graphiques',
            'priority': 14,
            'dependencies': []
        },
        'analytics': {
            'resources': ['maps', 'visualizations', 'eventReports', 'dashboards'],
            'description': 'Analytics et visualisations',
            'priority': 15,
            'dependencies': ['indicators', 'data_elements', 'programs', 'legends']
        },
        'misc': {
            'resources': ['documents', 'interpretations'],
            'description': 'Éléments divers',
            'priority': 16,
            'dependencies': []
        }
    }

    # Ordre d'import détaillé par ressource
    IMPORT_ORDER = {
        # NIVEAU 1: Users et rôles
        'userRoles': 1,
        'users': 2,
        'userGroups': 3,

        # NIVEAU 2: Organisation
        'organisationUnitLevels': 4,
        'organisationUnits': 5,
        'organisationUnitGroups': 6,
        'organisationUnitGroupSets': 7,

        # NIVEAU 3: Catégories
        'categoryOptions': 8,
        'categories': 9,
        'categoryCombos': 10,
        'categoryOptionGroups': 11,
        'categoryOptionGroupSets': 12,

        # NIVEAU 4: Options
        'options': 13,
        'optionSets': 14,

        # NIVEAU 5: Attributs et constantes
        'attributes': 15,
        'constants': 16,

        # NIVEAU 6: Éléments de données
        'dataElements': 17,
        'dataElementGroups': 18,
        'dataElementGroupSets': 19,

        # NIVEAU 7: Indicateurs
        'indicatorTypes': 20,
        'indicators': 21,
        'indicatorGroups': 22,
        'indicatorGroupSets': 23,

        # NIVEAU 8: Formulaires de saisie (avant dataSets)
        'dataEntryForms': 24,

        # NIVEAU 9: Ensembles de données
        'dataSets': 25,
        'dataSetElements': 26,
        'dataInputPeriods': 27,
        'dataSetNotificationTemplates': 28,

        # NIVEAU 10: Entités suivies
        'trackedEntityTypes': 29,
        'trackedEntityAttributes': 30,
        'trackedEntityAttributeGroups': 31,

        # NIVEAU 11: Relations
        'relationshipTypes': 32,

        # NIVEAU 12: Programmes
        'programs': 33,
        'programStageSections': 34,
        'programStages': 35,
        'programStageDataElements': 36,

        # NIVEAU 13: Actions de règles (AVANT les règles)
        'programRuleActions': 37,

        # NIVEAU 14: Indicateurs et règles de programmes
        'programIndicators': 38,
        'programRuleVariables': 39,
        'programRules': 40,
        'programNotificationTemplates': 41,

        # NIVEAU 15: Validation
        'validationRules': 42,
        'validationRuleGroups': 43,
        'validationNotificationTemplates': 44,

        # NIVEAU 16: Prédicteurs
        'predictors': 45,
        'predictorGroups': 46,

        # NIVEAU 17: Légendes
        'legends': 47,
        'legendSets': 48,

        # NIVEAU 18: Visualisations et analyses
        'maps': 49,
        'visualizations': 50,
        'eventReports': 51,
        'dashboards': 52,

        # NIVEAU 19: Documents et communications
        'documents': 53,
        'interpretations': 54,
    }

    def __init__(self, sync_config: SyncConfiguration):
        """
        Initialise le service de métadonnées

        Args:
            sync_config: Configuration de synchronisation contenant les instances source et destination
        """
        self.sync_config = sync_config
        self.source_instance = sync_config.source_instance
        self.destination_instance = sync_config.destination_instance
        self.logger = logger

    def get_ordered_families(self, selected_families: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Retourne les familles de métadonnées triées par ordre de priorité

        Args:
            selected_families: Liste des familles à synchroniser (toutes si None)

        Returns:
            Liste des familles triées par priorité
        """
        families = self.METADATA_FAMILIES_CONFIG

        if selected_families:
            families = {k: v for k, v in families.items() if k in selected_families}

        return sorted(families.items(), key=lambda x: x[1]['priority'])

    def get_ordered_resources(self, selected_families: Optional[List[str]] = None) -> List[str]:
        """
        Retourne toutes les ressources triées par ordre d'import

        Args:
            selected_families: Liste des familles à inclure (toutes si None)

        Returns:
            Liste des ressources triées
        """
        all_resources = []

        for family_name, family_config in self.get_ordered_families(selected_families):
            all_resources.extend(family_config['resources'])

        # Trier par ordre d'import
        return sorted(all_resources, key=lambda x: self.IMPORT_ORDER.get(x, 999))

    def clean_sharing_user_references(self, items: List[Dict[str, Any]], resource_name: str = '') -> List[Dict[str, Any]]:
        """
        Nettoie les références invalides dans le sharing pour éviter les erreurs lors de l'import.

        DHIS2 utilise deux formats de sharing :
        - Format API: 'users' et 'userGroups' (dict avec clés = user IDs)
        - Format import: 'userAccesses' et 'userGroupAccesses' (list d'objets)

        Cette méthode gère les deux formats et retire uniquement les utilisateurs/groupes
        qui n'existent pas dans la destination.

        Args:
            items: Liste des objets avec sharing
            resource_name: Nom de la ressource (pour les logs)

        Returns:
            Liste des objets avec sharing nettoyé
        """
        try:
            # Récupérer les users et userGroups existants dans la destination
            dest_users = self.destination_instance.get_metadata(
                resource='users',
                fields='id',
                paging=False
            )
            dest_user_ids = {u.get('id') for u in dest_users}

            dest_user_groups = self.destination_instance.get_metadata(
                resource='userGroups',
                fields='id',
                paging=False
            )
            dest_usergroup_ids = {ug.get('id') for ug in dest_user_groups}

            cleaned_count = 0
            removed_user_count = 0
            removed_usergroup_count = 0

            for item in items:
                if 'sharing' not in item or not isinstance(item['sharing'], dict):
                    continue

                sharing = item['sharing']
                item_cleaned = False

                # Format 1: 'users' (dict) - Format API
                if 'users' in sharing and isinstance(sharing['users'], dict):
                    original_count = len(sharing['users'])
                    # Garder seulement les users qui existent dans la destination
                    valid_users = {
                        uid: access for uid, access in sharing['users'].items()
                        if uid in dest_user_ids
                    }

                    if len(valid_users) < original_count:
                        removed = original_count - len(valid_users)
                        removed_user_count += removed
                        sharing['users'] = valid_users
                        item_cleaned = True

                # Format 2: 'userAccesses' (list) - Format import
                if 'userAccesses' in sharing and isinstance(sharing['userAccesses'], list):
                    original_count = len(sharing['userAccesses'])
                    valid_user_accesses = [
                        ua for ua in sharing['userAccesses']
                        if ua.get('id') in dest_user_ids
                    ]

                    if len(valid_user_accesses) < original_count:
                        removed = original_count - len(valid_user_accesses)
                        removed_user_count += removed
                        sharing['userAccesses'] = valid_user_accesses
                        item_cleaned = True

                # Format 1: 'userGroups' (dict) - Format API
                if 'userGroups' in sharing and isinstance(sharing['userGroups'], dict):
                    original_count = len(sharing['userGroups'])
                    valid_usergroups = {
                        uid: access for uid, access in sharing['userGroups'].items()
                        if uid in dest_usergroup_ids
                    }

                    if len(valid_usergroups) < original_count:
                        removed = original_count - len(valid_usergroups)
                        removed_usergroup_count += removed
                        sharing['userGroups'] = valid_usergroups
                        item_cleaned = True

                # Format 2: 'userGroupAccesses' (list) - Format import
                if 'userGroupAccesses' in sharing and isinstance(sharing['userGroupAccesses'], list):
                    original_count = len(sharing['userGroupAccesses'])
                    valid_usergroup_accesses = [
                        uga for uga in sharing['userGroupAccesses']
                        if uga.get('id') in dest_usergroup_ids
                    ]

                    if len(valid_usergroup_accesses) < original_count:
                        removed = original_count - len(valid_usergroup_accesses)
                        removed_usergroup_count += removed
                        sharing['userGroupAccesses'] = valid_usergroup_accesses
                        item_cleaned = True

                if item_cleaned:
                    cleaned_count += 1

            if cleaned_count > 0:
                resource_label = f" pour {resource_name}" if resource_name else ""
                self.logger.info(f"Nettoyé le sharing de {cleaned_count} objets{resource_label}: {removed_user_count} users invalides, {removed_usergroup_count} userGroups invalides retirés")

            return items

        except Exception as e:
            self.logger.warning(f"Erreur lors du nettoyage du sharing: {e}. Continuation sans nettoyage.")
            return items

    def validate_dependencies(self, families: List[str]) -> List[str]:
        """
        Valide et résout les dépendances entre familles

        Args:
            families: Liste des familles à synchroniser

        Returns:
            Liste des familles avec dépendances résolues
        """
        resolved_families = set()
        families_to_process = set(families)

        def resolve_family(family_name: str):
            if family_name in resolved_families:
                return

            family_config = self.METADATA_FAMILIES_CONFIG.get(family_name)
            if not family_config:
                self.logger.warning(f"Famille de métadonnées inconnue: {family_name}")
                return

            # Résoudre d'abord les dépendances
            for dependency in family_config.get('dependencies', []):
                if dependency not in resolved_families:
                    resolve_family(dependency)
                    families_to_process.add(dependency)

            resolved_families.add(family_name)

        # Résoudre toutes les familles
        for family in list(families_to_process):
            resolve_family(family)

        # Retourner dans l'ordre de priorité
        ordered_families = []
        for family_name, _ in self.get_ordered_families():
            if family_name in families_to_process:
                ordered_families.append(family_name)

        return ordered_families

    def check_instances_compatibility(self) -> Dict[str, Any]:
        """
        Vérifie la compatibilité entre les instances source et destination

        Returns:
            Dictionnaire avec les résultats de compatibilité
        """
        try:
            # Test de connexion source
            source_test = self.source_instance.test_connection()

            # Test de connexion destination
            dest_test = self.destination_instance.test_connection()

            compatibility = {
                'source_available': source_test['success'],
                'dest_available': dest_test['success'],
                'source_version': source_test.get('dhis2_version'),
                'dest_version': dest_test.get('dhis2_version'),
                'compatible': True,
                'warnings': [],
                'errors': []
            }

            if not source_test['success']:
                compatibility['errors'].append(f"Instance source inaccessible: {source_test['message']}")
                compatibility['compatible'] = False

            if not dest_test['success']:
                compatibility['errors'].append(f"Instance destination inaccessible: {dest_test['message']}")
                compatibility['compatible'] = False

            # Vérifications de versions
            if compatibility['source_available'] and compatibility['dest_available']:
                source_version = compatibility['source_version']
                dest_version = compatibility['dest_version']

                if source_version and dest_version:
                    if source_version != dest_version:
                        compatibility['warnings'].append(
                            f"Versions différentes: source ({source_version}) vs destination ({dest_version})"
                        )

            return compatibility

        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de compatibilité: {e}")
            return {
                'source_available': False,
                'dest_available': False,
                'compatible': False,
                'errors': [str(e)]
            }

    def fetch_metadata_resource(self, resource: str, fields: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère une ressource de métadonnées depuis l'instance source

        Args:
            resource: Nom de la ressource (ex: 'dataElements')
            fields: Champs à récupérer (optionnel)

        Returns:
            Liste des objets de métadonnées
        """
        try:
            self.logger.info(f"Récupération de la ressource: {resource}")

            # Utiliser des champs par défaut si non spécifiés
            if not fields:
                fields = "id,name,code,displayName,created,lastUpdated"

            data = self.source_instance.get_metadata(
                resource=resource,
                fields=fields,
                paging=True,
                page_size=100
            )

            self.logger.info(f"Récupérés {len(data)} éléments pour {resource}")
            return data

        except Exception as e:
            error_str = str(e)
            # Gérer gracieusement les ressources non disponibles (404)
            if "404" in error_str or "Not Found" in error_str:
                self.logger.warning(f"Ressource {resource} non disponible sur l'instance source (404) - ignorée")
                return []

            self.logger.error(f"Erreur lors de la récupération de {resource}: {e}")
            raise MetadataServiceError(f"Impossible de récupérer {resource}: {str(e)}")

    def import_metadata_resource(self, resource: str, data: List[Dict[str, Any]],
                                strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """
        Importe une ressource de métadonnées vers l'instance destination

        Args:
            resource: Nom de la ressource
            data: Données à importer
            strategy: Stratégie d'import

        Returns:
            Résultat de l'import
        """
        try:
            if not data:
                self.logger.info(f"Aucune donnée à importer pour {resource}")
                return {'status': 'OK', 'message': 'Aucune donnée à importer'}

            self.logger.info(f"Import de {len(data)} éléments pour {resource}")

            result = self.destination_instance.post_metadata(
                resource=resource,
                data=data,
                strategy=strategy
            )

            self.logger.info(f"Import terminé pour {resource}: {result.get('status', 'Unknown')}")
            return result

        except Exception as e:
            self.logger.error(f"Erreur lors de l'import de {resource}: {e}")
            raise MetadataServiceError(f"Impossible d'importer {resource}: {str(e)}")

    def sync_metadata_resource(self, resource: str, job: Optional[SyncJob] = None,
                              strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """
        Synchronise une ressource de métadonnées complète (fetch + import)

        Args:
            resource: Nom de la ressource à synchroniser
            job: Job de synchronisation (optionnel)
            strategy: Stratégie d'import

        Returns:
            Résultat de la synchronisation
        """
        try:
            # Mettre à jour le job si fourni
            if job:
                job.log_message += f"Synchronisation de {resource}...\n"
                job.save()

            # Récupérer les données
            data = self.fetch_metadata_resource(resource)

            # Mettre à jour les statistiques du job
            if job:
                job.total_items += len(data)
                job.save()

            # Si aucune donnée, retourner succès
            if not data:
                if job:
                    job.log_message += self._format_sync_log(resource, 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {
                    'resource': resource,
                    'success': True,
                    'imported_count': 0,
                    'error_count': 0,
                    'result': {'status': 'OK', 'message': 'Aucune donnée à importer'}
                }

            # Importer les données
            result = self.import_metadata_resource(resource, data, strategy)

            # Analyser le résultat pour les statistiques
            stats = self._analyze_import_result(result)

            if job:
                job.processed_items += len(data)
                job.success_count += stats.get('imported', 0)
                job.error_count += stats.get('errors', 0)
                job.warning_count += stats.get('warnings', 0)
                job.log_message += self._format_sync_log(resource, len(data), stats)
                job.save()

            return {
                'resource': resource,
                'success': True,
                'imported_count': stats.get('imported', 0),
                'error_count': stats.get('errors', 0),
                'result': result
            }

        except Exception as e:
            error_msg = f"Erreur synchronisation {resource}: {str(e)}"
            self.logger.error(error_msg)

            if job:
                job.error_count += 1
                job.log_message += f"ERREUR {resource}: {str(e)}\n"
                job.save()

            return {
                'resource': resource,
                'success': False,
                'error': str(e)
            }

    def _analyze_import_result(self, result: Dict[str, Any]) -> Dict[str, int]:
        """
        Analyse le résultat d'un import DHIS2 pour extraire les statistiques

        Args:
            result: Résultat de l'import DHIS2

        Returns:
            Statistiques extraites
        """
        stats = {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0}

        try:
            # Gérer les deux formats de réponse DHIS2
            # Format 1: {"importSummary": {...}} - pour les données agrégées
            # Format 2: {"response": {"typeReports": [...]}} - pour les métadonnées

            # Extraire la réponse (peut être directement result ou dans result['response'])
            response = result.get('response', result)

            # Structure typique de réponse DHIS2 pour les données
            if 'importSummary' in response:
                summary = response['importSummary']
                stats['imported'] = summary.get('importCount', 0)
                stats['updated'] = summary.get('updateCount', 0)
                stats['ignored'] = summary.get('ignoredCount', 0)
                stats['errors'] = len(summary.get('conflicts', []))

            # Format pour les métadonnées
            elif 'typeReports' in response:
                for type_report in response['typeReports']:
                    type_stats = type_report.get('stats', {})
                    stats['imported'] += type_stats.get('created', 0)
                    stats['updated'] += type_stats.get('updated', 0)
                    stats['ignored'] += type_stats.get('ignored', 0)

                    object_reports = type_report.get('objectReports', [])
                    for obj_report in object_reports:
                        error_reports = obj_report.get('errorReports', [])
                        if error_reports:
                            stats['errors'] += len(error_reports)

        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse du résultat d'import: {e}")

        return stats

    def _format_sync_log(self, resource: str, source_count: int, stats: Dict[str, int]) -> str:
        """
        Formate un message de log détaillé pour une synchronisation de ressource

        Args:
            resource: Nom de la ressource (ex: 'programs', 'dataElements')
            source_count: Nombre d'éléments récupérés de la source
            stats: Statistiques d'import (imported, updated, ignored, errors, warnings)

        Returns:
            Message de log formaté
        """
        created = stats.get('imported', 0)
        updated = stats.get('updated', 0)
        ignored = stats.get('ignored', 0)
        errors = stats.get('errors', 0)
        warnings = stats.get('warnings', 0)

        # Format: ✓ resource: Source=X | Created=Y, Updated=Z | Ignored=W | Errors=E, Warnings=W
        log_parts = [
            f"Source={source_count}",
            f"Created={created}, Updated={updated}",
            f"Ignored={ignored}",
            f"Errors={errors}, Warnings={warnings}"
        ]

        return f"✓ {resource}: {' | '.join(log_parts)}\n"