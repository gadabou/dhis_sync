"""
Service de synchronisation des données tracker DHIS2
"""
import logging
from typing import Dict, List, Any, Optional
from django.utils import timezone
from .base import BaseDataService, DataServiceError
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class TrackerDataService(BaseDataService):
    """Service de synchronisation des données tracker DHIS2"""

    def sync_tracker_data(self, job: SyncJob, programs: Optional[List[str]] = None,
                         org_units: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Synchronise les données tracker (TEI + enrollments + events)

        Args:
            job: Job de synchronisation
            programs: Liste des UIDs de programmes tracker (optionnel)
            org_units: Liste des UIDs d'unités d'organisation (optionnel)

        Returns:
            Résultat de la synchronisation
        """
        try:
            job.status = 'running'
            job.started_at = timezone.now()
            job.log_message += "=== DÉBUT SYNCHRONISATION DONNÉES TRACKER ===\n"
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

            # Récupérer la liste des programmes tracker si non fournie
            if not programs:
                programs = self._get_available_tracker_programs()

            if not programs:
                job.status = 'completed'
                job.log_message += "Aucun programme tracker trouvé pour la synchronisation\n"
                job.save()
                return {'success': True, 'imported_count': 0, 'message': 'Aucun programme tracker disponible'}

            job.log_message += f"Programmes tracker à synchroniser: {len(programs)}\n"
            job.save()

            # Synchroniser chaque programme
            total_imported = 0
            total_errors = 0
            program_results = {}

            for i, program_uid in enumerate(programs):
                try:
                    program_result = self.sync_tracker_program(
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
                    error_msg = f"Erreur programme tracker {program_uid}: {str(e)}"
                    self.logger.error(error_msg)
                    program_results[program_uid] = {'success': False, 'error': str(e)}
                    total_errors += 1

            # Finaliser le job
            job.completed_at = timezone.now()
            job.progress = 100

            if total_errors == 0:
                job.status = 'completed'
                job.log_message += f"=== SYNCHRONISATION RÉUSSIE - {total_imported} éléments tracker importés ===\n"
            elif total_errors < len(programs):
                job.status = 'completed_with_warnings'
                job.log_message += f"=== SYNCHRONISATION TERMINÉE AVEC AVERTISSEMENTS - {total_imported} éléments importés, {total_errors} programmes en erreur ===\n"
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
            error_msg = f"Erreur critique lors de la synchronisation des données tracker: {str(e)}"
            self.logger.error(error_msg)

            job.status = 'failed'
            job.completed_at = timezone.now()
            job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
            job.save()

            return {'success': False, 'error': error_msg}

    def sync_tracker_program(self, job: SyncJob, program_uid: str,
                            org_units: Optional[List[str]] = None,
                            date_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Synchronise les données tracker d'un programme spécifique

        Args:
            job: Job de synchronisation
            program_uid: UID du programme tracker
            org_units: Liste des unités d'organisation
            date_range: Plage de dates

        Returns:
            Résultat de la synchronisation du programme
        """
        try:
            job.log_message += f"Synchronisation programme tracker {program_uid}...\n"
            job.save()

            # Récupérer les TEI avec leurs enrollments et events
            tei_data = self.fetch_tracker_program_data(
                program_uid=program_uid,
                org_units=org_units,
                date_range=date_range
            )

            if not tei_data:
                job.log_message += f"Aucune donnée tracker trouvée pour le programme {program_uid}\n"
                return {'success': True, 'imported_count': 0, 'tei_data': {}}

            tei_count = len(tei_data.get('trackedEntities', []))
            enrollment_count = len(tei_data.get('enrollments', []))
            event_count = len(tei_data.get('events', []))

            job.log_message += f"Programme {program_uid}: {tei_count} TEI, {enrollment_count} enrollments, {event_count} events\n"
            job.total_items += tei_count + enrollment_count + event_count
            job.save()

            # Importer les données tracker
            result = self.import_tracker_data(tei_data, job)

            # Analyser les résultats
            stats = self._analyze_tracker_import_result(result)

            total_imported = stats.get('tei_imported', 0) + stats.get('enrollments_imported', 0) + stats.get('events_imported', 0)
            total_errors = stats.get('errors', 0)

            job.processed_items += tei_count + enrollment_count + event_count
            job.success_count += total_imported
            job.error_count += total_errors

            # Log détaillé
            source_total = tei_count + enrollment_count + event_count
            job.log_message += self._format_sync_log(f"Programme {program_uid}", source_total, {
                'imported': total_imported,
                'updated': 0,
                'ignored': 0,
                'deleted': 0,
                'errors': total_errors
            })
            job.save()

            return {
                'success': total_errors == 0,
                'imported_count': total_imported,
                'error_count': total_errors,
                'tei_data': tei_data,
                'result': result
            }

        except Exception as e:
            error_msg = f"Erreur synchronisation programme tracker {program_uid}: {str(e)}"
            self.logger.error(error_msg)
            job.log_message += f"ERREUR programme tracker {program_uid}: {error_msg}\n"
            job.save()

            return {'success': False, 'error': error_msg}

    def fetch_tracker_program_data(self, program_uid: str, org_units: Optional[List[str]] = None,
                                  date_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Récupère toutes les données tracker d'un programme (TEI + enrollments + events)

        Args:
            program_uid: UID du programme
            org_units: Liste des unités d'organisation
            date_range: Plage de dates

        Returns:
            Dictionnaire avec toutes les données tracker
        """
        try:
            self.logger.info(f"Récupération des données tracker du programme {program_uid}")

            # Paramètres par défaut
            last_updated_start = date_range.get('start_date') if date_range else '2020-01-01'
            last_updated_end = date_range.get('end_date') if date_range else timezone.now().strftime('%Y-%m-%d')

            all_tei_data = {
                'trackedEntities': [],
                'enrollments': [],
                'events': []
            }

            # Si des unités d'organisation sont spécifiées, les traiter une par une
            if org_units:
                valid_org_units = self.validate_org_units(org_units)

                if not valid_org_units:
                    self.logger.warning(f"Aucune orgUnit valide trouvée dans la source pour le programme {program_uid}")
                    return all_tei_data

                for org_unit in valid_org_units:
                    try:
                        tei_response = self.source_instance.get_tracked_entity_instances(
                            program=program_uid,
                            orgUnit=org_unit,
                            ouMode='DESCENDANTS',
                            lastUpdatedStartDate=last_updated_start,
                            lastUpdatedEndDate=last_updated_end,
                            paging='false'
                        )

                        # Extraire les TEI
                        teis = tei_response.get('trackedEntityInstances', [])
                        all_tei_data['trackedEntities'].extend(teis)

                        # Extraire les enrollments et events des TEI
                        for tei in teis:
                            enrollments = tei.get('enrollments', [])
                            all_tei_data['enrollments'].extend(enrollments)

                            for enrollment in enrollments:
                                events = enrollment.get('events', [])
                                all_tei_data['events'].extend(events)

                    except Exception as e:
                        error_msg = str(e)
                        if "At least one organisation unit must be specified" in error_msg:
                            self.logger.warning(
                                f"OrgUnit {org_unit} inaccessible ou invalide pour le programme {program_uid}. "
                                f"Cela peut indiquer que l'orgUnit n'existe pas dans DHIS2 source ou que l'utilisateur n'y a pas accès."
                            )
                        else:
                            self.logger.warning(f"Erreur récupération TEI pour orgUnit {org_unit}: {e}")
                        continue
            else:
                # Récupérer toutes les TEI du programme
                try:
                    # Récupérer les orgUnits assignées à ce programme
                    program_details = self.source_instance.get_metadata(
                        'programs',
                        fields='id,name,organisationUnits[id]',
                        paging=False
                    )

                    program_orgunits = []
                    for prog in program_details:
                        if prog.get('id') == program_uid:
                            org_units_list = prog.get('organisationUnits', [])
                            program_orgunits = [ou.get('id') for ou in org_units_list if ou.get('id')]
                            break

                    if program_orgunits:
                        # Utiliser les orgUnits assignées au programme
                        self.logger.info(f"Programme {program_uid}: {len(program_orgunits)} orgUnits assignées")

                        # Limiter le nombre d'orgUnits pour éviter une requête trop lourde
                        max_orgunits = 10
                        selected_orgunits = program_orgunits[:max_orgunits]

                        if len(program_orgunits) > max_orgunits:
                            self.logger.warning(f"Limitation à {max_orgunits} orgUnits sur {len(program_orgunits)} disponibles")

                        for org_unit in selected_orgunits:
                            try:
                                tei_response = self.source_instance.get_tracked_entity_instances(
                                    program=program_uid,
                                    orgUnit=org_unit,
                                    ouMode='DESCENDANTS',
                                    lastUpdatedStartDate=last_updated_start,
                                    lastUpdatedEndDate=last_updated_end,
                                    paging='false'
                                )

                                # Extraire les TEI
                                teis = tei_response.get('trackedEntityInstances', [])
                                all_tei_data['trackedEntities'].extend(teis)

                                # Extraire les enrollments et events des TEI
                                for tei in teis:
                                    enrollments = tei.get('enrollments', [])
                                    all_tei_data['enrollments'].extend(enrollments)

                                    for enrollment in enrollments:
                                        events = enrollment.get('events', [])
                                        all_tei_data['events'].extend(events)

                            except Exception as e:
                                error_msg = str(e)
                                if "At least one organisation unit must be specified" in error_msg:
                                    self.logger.warning(
                                        f"OrgUnit {org_unit} inaccessible ou invalide pour le programme {program_uid}. "
                                        f"Cela peut indiquer que l'orgUnit n'existe pas dans DHIS2 source ou que l'utilisateur n'y a pas accès."
                                    )
                                else:
                                    self.logger.warning(f"Erreur récupération TEI pour orgUnit {org_unit}: {e}")
                                continue
                    else:
                        self.logger.warning(f"Aucune orgUnit assignée au programme {program_uid}")

                except Exception as e:
                    self.logger.warning(f"Erreur récupération TEI globale: {e}")

            tei_count = len(all_tei_data['trackedEntities'])
            enrollment_count = len(all_tei_data['enrollments'])
            event_count = len(all_tei_data['events'])

            self.logger.info(f"Programme {program_uid}: {tei_count} TEI, {enrollment_count} enrollments, {event_count} events")
            return all_tei_data

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des données tracker du programme {program_uid}: {e}")
            raise DataServiceError(f"Impossible de récupérer les données tracker du programme {program_uid}: {str(e)}")

    def import_tracker_data(self, tei_data: Dict[str, Any], job: Optional[SyncJob] = None) -> Dict[str, Any]:
        """
        Importe les données tracker vers l'instance destination

        Args:
            tei_data: Données tracker à importer
            job: Job de synchronisation (optionnel)

        Returns:
            Résultat de l'import
        """
        try:
            if not any(tei_data.values()):
                return {'status': 'OK', 'message': 'Aucune donnée tracker à importer'}

            tei_count = len(tei_data.get('trackedEntities', []))
            enrollment_count = len(tei_data.get('enrollments', []))
            event_count = len(tei_data.get('events', []))

            self.logger.info(f"Import de données tracker: {tei_count} TEI, {enrollment_count} enrollments, {event_count} events")

            if job:
                job.log_message += f"Import tracker: {tei_count} TEI, {enrollment_count} enrollments, {event_count} events\n"
                job.save()

            # Utiliser l'import tracker bundle pour importer tout en une fois
            result = self.destination_instance.import_tracker_bundle(
                tracked_entities=tei_data.get('trackedEntities'),
                enrollments=tei_data.get('enrollments'),
                events=tei_data.get('events'),
                strategy='CREATE_AND_UPDATE',
                atomic_mode='NONE'
            )

            self.logger.info(f"Import tracker terminé: {result.get('status', 'Unknown')}")
            return result

        except Exception as e:
            self.logger.error(f"Erreur lors de l'import des données tracker: {e}")
            raise DataServiceError(f"Impossible d'importer les données tracker: {str(e)}")

    def _get_available_tracker_programs(self) -> List[str]:
        """
        Récupère la liste des programmes tracker disponibles sur l'instance source

        Returns:
            Liste des UIDs de programmes tracker
        """
        try:
            programs = self.source_instance.get_metadata(
                'programs',
                fields='id,name,programType',
                paging=False
            )

            # Filtrer les programmes tracker
            tracker_programs = []
            for program in programs:
                if program.get('programType') == 'WITH_REGISTRATION':
                    tracker_programs.append(program.get('id'))

            self.logger.info(f"Trouvés {len(tracker_programs)} programmes tracker")
            return tracker_programs

        except Exception as e:
            self.logger.warning(f"Erreur récupération programmes tracker: {e}")
            return []

    def _analyze_tracker_import_result(self, result: Dict[str, Any]) -> Dict[str, int]:
        """
        Analyse le résultat d'un import tracker pour extraire les statistiques

        Args:
            result: Résultat de l'import tracker

        Returns:
            Statistiques extraites spécifiques au tracker
        """
        stats = {
            'tei_imported': 0, 'tei_updated': 0,
            'enrollments_imported': 0, 'enrollments_updated': 0,
            'events_imported': 0, 'events_updated': 0,
            'errors': 0
        }

        try:
            # Structure pour les bundles tracker
            if 'bundleReport' in result:
                bundle_report = result['bundleReport']
                type_report_map = bundle_report.get('typeReportMap', {})

                # TEI
                if 'TRACKED_ENTITY' in type_report_map:
                    tei_stats = type_report_map['TRACKED_ENTITY'].get('stats', {})
                    stats['tei_imported'] = tei_stats.get('created', 0)
                    stats['tei_updated'] = tei_stats.get('updated', 0)

                    # Erreurs TEI
                    tei_reports = type_report_map['TRACKED_ENTITY'].get('objectReports', [])
                    for report in tei_reports:
                        if report.get('errorReports'):
                            stats['errors'] += len(report['errorReports'])

                # Enrollments
                if 'ENROLLMENT' in type_report_map:
                    enr_stats = type_report_map['ENROLLMENT'].get('stats', {})
                    stats['enrollments_imported'] = enr_stats.get('created', 0)
                    stats['enrollments_updated'] = enr_stats.get('updated', 0)

                    # Erreurs Enrollments
                    enr_reports = type_report_map['ENROLLMENT'].get('objectReports', [])
                    for report in enr_reports:
                        if report.get('errorReports'):
                            stats['errors'] += len(report['errorReports'])

                # Events
                if 'EVENT' in type_report_map:
                    event_stats = type_report_map['EVENT'].get('stats', {})
                    stats['events_imported'] = event_stats.get('created', 0)
                    stats['events_updated'] = event_stats.get('updated', 0)

                    # Erreurs Events
                    event_reports = type_report_map['EVENT'].get('objectReports', [])
                    for report in event_reports:
                        if report.get('errorReports'):
                            stats['errors'] += len(report['errorReports'])

            # Structure legacy fallback
            elif 'reports' in result:
                reports = result['reports']

                for report_name, report_data in reports.items():
                    if 'trackedEntityInstances' in report_name:
                        summary = report_data.get('importSummary', {})
                        stats['tei_imported'] += summary.get('importCount', 0)
                        stats['tei_updated'] += summary.get('updateCount', 0)
                        stats['errors'] += len(summary.get('conflicts', []))

                    elif 'enrollments' in report_name:
                        summary = report_data.get('importSummary', {})
                        stats['enrollments_imported'] += summary.get('importCount', 0)
                        stats['enrollments_updated'] += summary.get('updateCount', 0)
                        stats['errors'] += len(summary.get('conflicts', []))

                    elif 'events' in report_name:
                        summary = report_data.get('importSummary', {})
                        stats['events_imported'] += summary.get('importCount', 0)
                        stats['events_updated'] += summary.get('updateCount', 0)
                        stats['errors'] += len(summary.get('conflicts', []))

        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse du résultat d'import tracker: {e}")

        return stats
