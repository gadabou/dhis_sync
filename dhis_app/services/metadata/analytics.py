"""
Service de synchronisation des visualisations et dashboards DHIS2
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class VisualizationsService(BaseMetadataService):
    """Service de synchronisation des visualisations"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les visualisations"""
        try:
            if job:
                job.log_message += "Synchronisation de visualizations...\n"
                job.save()

            visualizations = self.source_instance.get_metadata(
                resource='visualizations',
                fields='id,name,displayName,type,dataDimensionItems,columns,rows,filters,organisationUnits,periods,sharing',
                paging=False
            )


            source_count = len(visualizations)

            if not visualizations:
                if job:
                    job.log_message += self._format_sync_log('visualizations', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            visualizations = self.clean_sharing_user_references(visualizations, 'visualizations')

            # Nettoyer les références aux categoryCombo et autres objets qui peuvent causer des erreurs
            visualizations = self.clean_visualization_references(visualizations)

            # Utiliser skipSharing=True pour éviter les erreurs de proxy Hibernate liées au sharing
            # Le sharing sera géré séparément si nécessaire
            result = self.destination_instance.post_metadata(
                resource='visualizations',
                data=visualizations,
                strategy=strategy,
                skip_sharing=True
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('visualizations', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_str = str(e)
            # Gérer gracieusement les ressources non disponibles (404)
            if "404" in error_str or "Not Found" in error_str:
                self.logger.warning(f"Ressource visualizations non disponible sur l'instance source (404) - ignorée")
                if job:
                    job.log_message += "INFO: Ressource visualizations non disponible (404) - ignorée\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            error_msg = f"Impossible d'importer visualizations: {error_str}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR visualizations: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class MapsService(BaseMetadataService):
    """Service de synchronisation des cartes"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les cartes"""
        try:
            if job:
                job.log_message += "Synchronisation de maps...\n"
                job.save()

            maps = self.source_instance.get_metadata(
                resource='maps',
                fields='id,name,displayName,mapViews,sharing',
                paging=False
            )


            source_count = len(maps)

            if not maps:
                if job:
                    job.log_message += self._format_sync_log('maps', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références invalides dans le sharing
            maps = self.clean_sharing_user_references(maps, 'maps')

            result = self.destination_instance.post_metadata(
                resource='maps',
                data=maps,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('maps', source_count, stats)
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "Not Found" in error_str:
                self.logger.warning(f"Ressource maps non disponible sur l'instance source (404) - ignorée")
                if job:
                    job.log_message += "INFO: Ressource maps non disponible (404) - ignorée\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            error_msg = f"Impossible d'importer maps: {error_str}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR maps: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}