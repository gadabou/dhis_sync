"""
Service de synchronisation des événements DHIS2
"""
import logging
from typing import Dict, List, Any, Optional
from django.utils import timezone
from .base import BaseDataService, DataServiceError
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class EventsDataService(BaseDataService):
    """Service de synchronisation des événements DHIS2"""

    def sync_events_data(self, job: SyncJob, programs: Optional[List[str]] = None,
                        org_units: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Synchronise les événements

        Args:
            job: Job de synchronisation
            programs: Liste des UIDs de programmes (optionnel)
            org_units: Liste des UIDs d'unités d'organisation (optionnel)

        Returns:
            Résultat de la synchronisation
        """
        try:
            job.status = 'running'
            job.started_at = timezone.now()
            job.log_message += "=== DÉBUT SYNCHRONISATION ÉVÉNEMENTS ===\n"
            job.save()

            # Vérifier la compatibilité
            compatibility = self.check_instances_compatibility()
            if not compatibility['compatible']:
                error_msg = "Instances incompatibles: " + "; ".join(compatibility['errors'])
                job.status = 'failed'
                job.log_message += f"ERREUR: {error_msg}\n"
                job.save()
                return {'success': False, 'error': error_msg}

            # Obtenir les paramètres de synchronisation
            sync_config = job.sync_config
            date_range = self.get_date_range_from_config(sync_config)

            # Récupérer la liste des programmes si non fournie
            if not programs:
                programs = self._get_available_programs()

            if not programs:
                job.status = 'completed'
                job.log_message += "Aucun programme trouvé pour la synchronisation des événements\n"
                job.save()
                return {'success': True, 'imported_count': 0, 'message': 'Aucun programme disponible'}

            job.log_message += f"Programmes à synchroniser: {len(programs)}\n"
            job.save()

            # Synchroniser chaque programme
            total_imported = 0
            total_errors = 0
            program_results = {}

            for i, program_uid in enumerate(programs):
                try:
                    program_result = self.sync_program_events(
                        job=job,
                        program_uid=program_uid,
                        org_units=org_units,
                        date_range=date_range
                    )

                    program_results[program_uid] = program_result
                    total_imported += program_result.get('imported_count', 0)
                    if not program_result['success']:
                        total_errors += 1

                    # Mettre à jour le progrès
                    progress = ((i + 1) / len(programs)) * 100
                    job.progress = int(progress * 0.9)  # 90% pour les programmes, 10% pour finalisation
                    job.save()

                except Exception as e:
                    error_msg = f"Erreur programme {program_uid}: {str(e)}"
                    self.logger.error(error_msg)
                    program_results[program_uid] = {'success': False, 'error': str(e)}
                    total_errors += 1

            # Finaliser le job
            job.completed_at = timezone.now()
            job.progress = 100

            if total_errors == 0:
                job.status = 'completed'
                job.log_message += f"=== SYNCHRONISATION RÉUSSIE - {total_imported} événements importés ===\n"
            elif total_errors < len(programs):
                job.status = 'completed_with_warnings'
                job.log_message += f"=== SYNCHRONISATION TERMINÉE AVEC AVERTISSEMENTS - {total_imported} événements importés, {total_errors} programmes en erreur ===\n"
            else:
                job.status = 'failed'
                job.log_message += f"=== SYNCHRONISATION ÉCHOUÉE - {total_errors} programmes en erreur ===\n"

            job.save()

            return {
                'success': total_errors < len(programs),
                'imported_count': total_imported,
                'error_count': total_errors,
                'programs': program_results
            }

        except Exception as e:
            error_msg = f"Erreur critique lors de la synchronisation des événements: {str(e)}"
            self.logger.error(error_msg)

            job.status = 'failed'
            job.completed_at = timezone.now()
            job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
            job.save()

            return {'success': False, 'error': error_msg}

    def sync_program_events(self, job: SyncJob, program_uid: str,
                           org_units: Optional[List[str]] = None,
                           date_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Synchronise les événements d'un programme spécifique

        Args:
            job: Job de synchronisation
            program_uid: UID du programme
            org_units: Liste des unités d'organisation
            date_range: Plage de dates

        Returns:
            Résultat de la synchronisation du programme
        """
        try:
            job.log_message += f"Synchronisation programme {program_uid}...\n"
            job.save()

            # Récupérer les événements
            events = self.fetch_program_events(
                program_uid=program_uid,
                org_units=org_units,
                date_range=date_range
            )

            if not events:
                job.log_message += f"Aucun événement trouvé pour le programme {program_uid}\n"
                return {'success': True, 'imported_count': 0, 'events': []}

            job.log_message += f"Trouvé {len(events)} événements pour le programme {program_uid}\n"
            job.total_items += len(events)
            job.save()

            # Importer les événements
            result = self.import_events(events, job)

            # Analyser les résultats
            stats = self._analyze_import_result(result)

            job.processed_items += len(events)
            job.success_count += stats.get('imported', 0) + stats.get('updated', 0)
            job.error_count += stats.get('errors', 0)
            job.log_message += f"Programme {program_uid}: {stats.get('imported', 0)} importés, {stats.get('errors', 0)} erreurs\n"
            job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0),
                'updated_count': stats.get('updated', 0),
                'error_count': stats.get('errors', 0),
                'events': events,
                'result': result
            }

        except Exception as e:
            error_msg = f"Erreur synchronisation programme {program_uid}: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR programme {program_uid}: {error_msg}\n"
            job.save()

            return {'success': False, 'error': error_msg}

    def fetch_program_events(self, program_uid: str, org_units: Optional[List[str]] = None,
                            date_range: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Récupère les événements d'un programme depuis l'instance source

        Args:
            program_uid: UID du programme
            org_units: Liste des unités d'organisation
            date_range: Plage de dates

        Returns:
            Liste des événements
        """
        try:
            self.logger.info(f"Récupération des événements du programme {program_uid}")

            # Paramètres par défaut
            start_date = date_range.get('start_date') if date_range else '2020-01-01'
            end_date = date_range.get('end_date') if date_range else timezone.now().strftime('%Y-%m-%d')

            all_events = []

            # Si des unités d'organisation sont spécifiées, les traiter une par une
            if org_units:
                valid_org_units = self.validate_org_units(org_units)

                for org_unit in valid_org_units:
                    try:
                        events = self.source_instance.get_events(
                            program=program_uid,
                            orgUnit=org_unit,
                            startDate=start_date,
                            endDate=end_date,
                            ouMode='SELECTED',
                            paging='false'
                        )

                        event_list = events.get('events', [])
                        all_events.extend(event_list)

                    except Exception as e:
                        self.logger.warning(f"Erreur récupération événements pour {org_unit}: {e}")
                        continue
            else:
                # Récupérer tous les événements du programme
                try:
                    # Utiliser une unité d'organisation racine si disponible
                    root_orgunits = self.source_instance.get_metadata(
                        'organisationUnits',
                        fields='id,level',
                        paging=False
                    )

                    # Trouver l'unité de niveau 1 (racine)
                    root_orgunit = None
                    for ou in root_orgunits:
                        if ou.get('level') == 1:
                            root_orgunit = ou.get('id')
                            break

                    if root_orgunit:
                        events = self.source_instance.get_events(
                            program=program_uid,
                            orgUnit=root_orgunit,
                            startDate=start_date,
                            endDate=end_date,
                            ouMode='DESCENDANTS',
                            paging='false'
                        )

                        all_events = events.get('events', [])

                except Exception as e:
                    self.logger.warning(f"Erreur récupération événements globale: {e}")
                    all_events = []

            self.logger.info(f"Récupérés {len(all_events)} événements pour le programme {program_uid}")
            return all_events

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des événements du programme {program_uid}: {e}")
            raise DataServiceError(f"Impossible de récupérer les événements du programme {program_uid}: {str(e)}")

    def import_events(self, events: List[Dict[str, Any]], job: Optional[SyncJob] = None) -> Dict[str, Any]:
        """
        Importe les événements vers l'instance destination

        Args:
            events: Liste des événements à importer
            job: Job de synchronisation (optionnel)

        Returns:
            Résultat de l'import
        """
        try:
            if not events:
                return {'status': 'OK', 'message': 'Aucun événement à importer'}

            self.logger.info(f"Import de {len(events)} événements")

            # Diviser en chunks pour éviter les timeouts
            chunks = self.chunk_data(events, chunk_size=500)
            total_results = []

            for i, chunk in enumerate(chunks):
                if job:
                    job.log_message += f"Import chunk événements {i+1}/{len(chunks)} ({len(chunk)} événements)...\n"
                    job.save()

                try:
                    result = self.destination_instance.import_events(
                        events=chunk,
                        strategy='CREATE_AND_UPDATE',
                        atomic_mode='NONE'
                    )

                    total_results.append(result)

                except Exception as e:
                    error_msg = f"Erreur import chunk événements {i+1}: {str(e)}"
                    self.logger.error(error_msg)
                    if job:
                        job.log_message += f"ERREUR: {error_msg}\n"
                        job.save()

                    # Continuer avec les autres chunks
                    total_results.append({
                        'status': 'ERROR',
                        'message': str(e)
                    })

            # Consolider les résultats
            consolidated_result = self._consolidate_events_results(total_results)

            self.logger.info(f"Import événements terminé: {consolidated_result.get('status', 'Unknown')}")
            return consolidated_result

        except Exception as e:
            self.logger.error(f"Erreur lors de l'import des événements: {e}")
            raise DataServiceError(f"Impossible d'importer les événements: {str(e)}")

    def _get_available_programs(self) -> List[str]:
        """
        Récupère la liste des programmes disponibles sur l'instance source

        Returns:
            Liste des UIDs de programmes
        """
        try:
            programs = self.source_instance.get_metadata(
                'programs',
                fields='id,name,programType',
                paging=False
            )

            # Filtrer les programmes événements (pas tracker)
            event_programs = []
            for program in programs:
                if program.get('programType') == 'WITHOUT_REGISTRATION':
                    event_programs.append(program.get('id'))

            self.logger.info(f"Trouvés {len(event_programs)} programmes événements")
            return event_programs

        except Exception as e:
            self.logger.warning(f"Erreur récupération programmes: {e}")
            return []

    def _consolidate_events_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Consolide les résultats de plusieurs imports d'événements

        Args:
            results: Liste des résultats d'import

        Returns:
            Résultat consolidé
        """
        consolidated = {
            'status': 'OK',
            'bundleReport': {
                'status': 'OK',
                'typeReportMap': {
                    'EVENT': {
                        'stats': {
                            'created': 0,
                            'updated': 0,
                            'ignored': 0,
                            'deleted': 0
                        },
                        'objectReports': []
                    }
                }
            }
        }

        total_errors = 0

        for result in results:
            try:
                if 'bundleReport' in result:
                    bundle_report = result['bundleReport']
                    type_report_map = bundle_report.get('typeReportMap', {})

                    for type_name, type_report in type_report_map.items():
                        if type_name == 'EVENT':
                            stats = type_report.get('stats', {})
                            consolidated_stats = consolidated['bundleReport']['typeReportMap']['EVENT']['stats']

                            consolidated_stats['created'] += stats.get('created', 0)
                            consolidated_stats['updated'] += stats.get('updated', 0)
                            consolidated_stats['ignored'] += stats.get('ignored', 0)
                            consolidated_stats['deleted'] += stats.get('deleted', 0)

                            object_reports = type_report.get('objectReports', [])
                            for obj_report in object_reports:
                                if obj_report.get('errorReports'):
                                    consolidated['bundleReport']['typeReportMap']['EVENT']['objectReports'].append(obj_report)
                                    total_errors += len(obj_report['errorReports'])

                elif result.get('status') == 'ERROR':
                    total_errors += 1

            except Exception as e:
                self.logger.warning(f"Erreur consolidation résultat événements: {e}")
                total_errors += 1

        # Déterminer le statut global
        if total_errors > 0:
            if total_errors == len(results):
                consolidated['status'] = 'ERROR'
                consolidated['bundleReport']['status'] = 'ERROR'
            else:
                consolidated['status'] = 'WARNING'

        return consolidated