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


            source_count = len(roles)

            if not roles:
                if job:
                    job.log_message += self._format_sync_log('userRoles', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='userRoles',
                data=roles,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('userRoles', source_count, stats)
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

    def __init__(self, sync_config):
        super().__init__(sync_config)
        self.roles_service = UserRolesService(sync_config)

    def sync(self, job: Optional[SyncJob] = None, strategy: str = 'CREATE_AND_UPDATE') -> Dict[str, Any]:
        """Synchronise les utilisateurs en nettoyant les références aux rôles invalides"""
        try:
            if job:
                job.log_message += "Synchronisation de users...\n"
                job.save()

            # Récupérer les utilisateurs (sans pagination pour avoir TOUS les users)
            users = self.source_instance.get_metadata(
                resource='users',
                fields='id,name,code,displayName,username,firstName,surname,email,phoneNumber,userRoles[id],userGroups[id],organisationUnits[id],dataViewOrganisationUnits[id]',
                paging=False
            )

            source_count = len(users)

            if not users:
                if job:
                    job.log_message += self._format_sync_log('users', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Nettoyer les références aux rôles invalides
            cleaned_users = self._clean_user_role_references(users, job)

            if not cleaned_users:
                if job:
                    job.log_message += self._format_sync_log('users', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            # Importer tous les utilisateurs (avec rôles nettoyés)
            result = self.destination_instance.post_metadata(
                resource='users',
                data=cleaned_users,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('users', source_count, stats)
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

    def _clean_user_role_references(self, users: List[Dict[str, Any]], job: Optional[SyncJob]) -> List[Dict[str, Any]]:
        """Nettoie les références aux rôles invalides et assigne un rôle par défaut si nécessaire"""
        try:
            # Récupérer les rôles disponibles dans la destination
            dest_roles = self.destination_instance.get_metadata(
                resource='userRoles',
                fields='id,name',
                paging=False
            )
            dest_role_ids = {role['id'] for role in dest_roles}

            # Trouver un rôle par défaut (le premier disponible, de préférence un rôle basique)
            default_role_id = None
            if dest_roles:
                # Chercher un rôle "Data Entry" ou similaire
                for role in dest_roles:
                    role_name = role.get('name', '').lower()
                    if any(keyword in role_name for keyword in ['data entry', 'user', 'basic']):
                        default_role_id = role['id']
                        break
                # Si aucun rôle basique, prendre le premier disponible
                if not default_role_id:
                    default_role_id = dest_roles[0]['id']

            cleaned_count = 0
            users_with_default_role_count = 0
            users_kept_count = 0

            for user in users:
                user_roles = user.get('userRoles', [])

                if user_roles:
                    # Nettoyer les rôles invalides
                    original_count = len(user_roles)
                    cleaned_roles = [
                        role for role in user_roles
                        if (role.get('id') if isinstance(role, dict) else role) in dest_role_ids
                    ]

                    if len(cleaned_roles) < original_count:
                        cleaned_count += 1

                    # Si aucun rôle valide, assigner le rôle par défaut
                    if not cleaned_roles and default_role_id:
                        user['userRoles'] = [{'id': default_role_id}]
                        users_with_default_role_count += 1
                    else:
                        user['userRoles'] = cleaned_roles
                        users_kept_count += 1
                else:
                    # User sans rôles du tout - assigner le rôle par défaut
                    if default_role_id:
                        user['userRoles'] = [{'id': default_role_id}]
                        users_with_default_role_count += 1

            if cleaned_count > 0 and job:
                job.log_message += f"  {cleaned_count} utilisateur(s) avec rôles nettoyés (références invalides retirées)\n"
                job.save()

            if users_with_default_role_count > 0 and job:
                job.log_message += f"  {users_with_default_role_count} utilisateur(s) avec rôle par défaut assigné\n"
                job.save()

            return users

        except Exception as e:
            self.logger.warning(f"Erreur lors du nettoyage des rôles utilisateurs: {e}")
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
                fields='id,name,displayName,code,managedGroups[id],sharing',
                paging=False
            )


            source_count = len(groups)

            if not groups:
                if job:
                    job.log_message += self._format_sync_log('userGroups', 0, {'imported': 0, 'updated': 0, 'ignored': 0, 'errors': 0, 'warnings': 0})
                    job.save()
                return {'success': True, 'imported_count': 0, 'error_count': 0}

            result = self.destination_instance.post_metadata(
                resource='userGroups',
                data=groups,
                strategy=strategy
            )

            stats = self._analyze_import_result(result)

            if job:
                job.log_message += self._format_sync_log('userGroups', source_count, stats)
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
        self.roles_service = UserRolesService(sync_config)
        self.users_service = UsersService(sync_config)
        self.groups_service = UserGroupsService(sync_config)

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
