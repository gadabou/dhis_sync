"""
Service de synchronisation des utilisateurs, rôles et groupes DHIS2
Respecte l'ordre d'importation DHIS2: userRoles -> users -> userGroups
"""
import logging
from typing import Dict, List, Any, Optional
from .base import BaseMetadataService
from ...models import SyncJob, SyncConfiguration

logger = logging.getLogger(__name__)


class UserRolesService(BaseMetadataService):
    """Service de synchronisation des rôles d'utilisateurs"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les rôles d'utilisateurs"""
        try:
            if job:
                job.log_message += "Synchronisation de userRoles...\n"
                job.save()

            roles = self.source_instance.get_metadata(
                resource='userRoles',
                fields='id,name,displayName,description,authorities',
                paging=False
            )

            if not roles:
                if job:
                    job.log_message += "Résultat userRoles: 0 importés, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='userRoles',
                data=roles,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Résultat userRoles: {stats.get('imported', 0)} importés, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer userRoles: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR userRoles: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class UsersService(BaseMetadataService):
    """Service de synchronisation des utilisateurs"""

    def __init__(self, source_instance, destination_instance):
        super().__init__(source_instance, destination_instance)
        self.roles_service = UserRolesService(source_instance, destination_instance)

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les utilisateurs en filtrant ceux sans rôles valides"""
        try:
            if job:
                job.log_message += "Synchronisation de users...\n"
                job.save()

            # Récupérer les utilisateurs
            users = self.source_instance.get_metadata(
                resource='users',
                fields='id,name,code,displayName,username,firstName,surname,email,phoneNumber,userRoles[id],userGroups[id],organisationUnits[id],dataViewOrganisationUnits[id]',
                paging=True,
                page_size=100
            )

            if not users:
                if job:
                    job.log_message += "Résultat users: 0 importés, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Filtrer les utilisateurs sans rôles valides
            valid_users = self._filter_users_with_valid_roles(users, job)

            if not valid_users:
                if job:
                    job.log_message += "Résultat users: 0 importés (tous filtrés), 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Importer les utilisateurs valides
            result = self.destination_instance.post_metadata(
                resource='users',
                data=valid_users,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Résultat users: {stats.get('imported', 0)} importés, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': True,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer users: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR users: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}

    def _filter_users_with_valid_roles(self, users: List[Dict[str, Any]], job: Optional[SyncJob]) -> List[Dict[str, Any]]:
        """Filtre les utilisateurs pour ne garder que ceux avec au moins un rôle valide"""
        try:
            # Récupérer les rôles disponibles dans la destination
            dest_roles = self.destination_instance.get_metadata(
                resource='userRoles',
                fields='id',
                paging=False
            )
            dest_role_ids = {role['id'] for role in dest_roles}

            # Filtrer
            valid_users = []
            filtered_count = 0

            for user in users:
                user_roles = user.get('userRoles', [])

                # Ignorer si pas de rôles
                if not user_roles:
                    filtered_count += 1
                    continue

                # Vérifier si au moins un rôle existe dans la destination
                has_valid_role = any(
                    (role.get('id') if isinstance(role, dict) else role) in dest_role_ids
                    for role in user_roles
                )

                if has_valid_role:
                    valid_users.append(user)
                else:
                    filtered_count += 1

            if filtered_count > 0 and job:
                job.log_message += f"  {filtered_count} utilisateur(s) filtré(s) (pas de rôles valides)\n"
                job.save()

            return valid_users

        except Exception as e:
            self.logger.warning(f"Erreur lors du filtrage des utilisateurs: {e}")
            return users  # En cas d'erreur, retourner tous les utilisateurs


class UserGroupsService(BaseMetadataService):
    """Service de synchronisation des groupes d'utilisateurs"""

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les groupes d'utilisateurs"""
        try:
            if job:
                job.log_message += "Synchronisation de userGroups...\n"
                job.save()

            groups = self.source_instance.get_metadata(
                resource='userGroups',
                fields='id,name,displayName,code,users[id],managedGroups[id]',
                paging=False
            )

            if not groups:
                if job:
                    job.log_message += "Résultat userGroups: 0 importés, 0 erreurs\n"
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='userGroups',
                data=groups,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += f"Résultat userGroups: {stats.get('imported', 0)} importés, {stats.get('errors', 0)} erreurs\n"
                job.save()

            return {
                'success': stats.get('errors', 0) == 0,
                'imported_count': stats.get('imported', 0) + stats.get('updated', 0),
                'error_count': stats.get('errors', 0)
            }

        except Exception as e:
            error_msg = f"Impossible d'importer userGroups: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR userGroups: {error_msg}\n"
                job.save()
            return {'success': False, 'imported_count': 0, 'error_count': 1}


class UsersSyncService:
    """
    Service orchestrateur pour la synchronisation des utilisateurs
    Respecte l'ordre DHIS2: userRoles -> users -> userGroups
    """

    def __init__(self, sync_config: SyncConfiguration):
        """Initialise avec une configuration de synchronisation"""
        self.sync_config = sync_config
        self.source = sync_config.source_instance
        self.dest = sync_config.destination_instance

        # Initialiser les services
        self.roles_service = UserRolesService(self.source, self.dest)
        self.users_service = UsersService(self.source, self.dest)
        self.groups_service = UserGroupsService(self.source, self.dest)

        self.logger = logger

    def sync_all(self, job: SyncJob) -> Dict[str, Any]:
        """
        Synchronise tous les éléments liés aux utilisateurs dans l'ordre correct

        Args:
            job: Job de synchronisation

        Returns:
            Résultat de la synchronisation
        """
        try:
            strategy = self.sync_config.import_strategy
            results = {}
            total_imported = 0
            total_errors = 0

            # 1. userRoles (obligatoire en premier)
            roles_result = self.roles_service.sync(job, strategy)
            results['userRoles'] = roles_result
            total_imported += roles_result.get('imported_count', 0)
            if not roles_result.get('success', False):
                total_errors += 1

            # 2. users (nécessite userRoles)
            users_result = self.users_service.sync(job, strategy)
            results['users'] = users_result
            total_imported += users_result.get('imported_count', 0)
            if not users_result.get('success', False):
                total_errors += 1

            # 3. userGroups (nécessite users)
            groups_result = self.groups_service.sync(job, strategy)
            results['userGroups'] = groups_result
            total_imported += groups_result.get('imported_count', 0)
            if not groups_result.get('success', False):
                total_errors += 1

            return {
                'success': total_errors == 0,
                'results': results,
                'total_imported': total_imported,
                'total_errors': total_errors
            }

        except Exception as e:
            error_msg = f"Erreur lors de la synchronisation des utilisateurs: {str(e)}"
            self.logger.error(error_msg)
            if job:
                job.log_message += f"ERREUR CRITIQUE: {error_msg}\n"
                job.save()
            return {'success': False, 'error': error_msg, 'total_imported': 0, 'total_errors': 1}
