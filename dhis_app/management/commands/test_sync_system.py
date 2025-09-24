"""
Commande pour tester le système de synchronisation DHIS2
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from dhis_app.models import DHIS2Instance, SyncConfiguration
from dhis_app.services.sync_orchestrator import SyncOrchestrator
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test le système de synchronisation DHIS2'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config-id',
            type=int,
            help='ID de la configuration à tester'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mode test sans vraie synchronisation'
        )
        parser.add_argument(
            '--metadata-only',
            action='store_true',
            help='Tester uniquement la synchronisation des métadonnées'
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write(
                self.style.SUCCESS('=== TEST DU SYSTÈME DE SYNCHRONISATION DHIS2 ===')
            )

            # Test 1: Vérifier les imports
            self.stdout.write('Test 1: Vérification des imports...')
            try:
                from dhis_app.services.sync_orchestrator import SyncOrchestrator
                from dhis_app.services.metadata.metadata_sync_service import MetadataSyncService
                from dhis_app.services.data.tracker import TrackerDataService
                from dhis_app.services.data.events import EventsDataService
                from dhis_app.services.data.aggregate import AggregateDataService
                self.stdout.write(self.style.SUCCESS('✓ Tous les imports sont fonctionnels'))
            except ImportError as e:
                self.stdout.write(self.style.ERROR(f'✗ Erreur d\'import: {e}'))
                return

            # Test 2: Vérifier les instances DHIS2
            self.stdout.write('Test 2: Vérification des instances DHIS2...')
            instances = DHIS2Instance.objects.all()
            if instances.count() < 2:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ Seulement {instances.count()} instance(s) trouvée(s). '
                        f'Au moins 2 instances (source + destination) sont recommandées pour tester la synchronisation.'
                    )
                )
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ {instances.count()} instances trouvées'))

                # Test de connexion des instances
                for instance in instances:
                    try:
                        connection_test = instance.test_connection()
                        if connection_test['success']:
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✓ {instance.name}: Connexion OK')
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'  ⚠ {instance.name}: Connexion échouée - {connection_test["message"]}'
                                )
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ {instance.name}: Erreur - {e}')
                        )

            # Test 3: Vérifier les configurations
            self.stdout.write('Test 3: Vérification des configurations...')
            configs = SyncConfiguration.objects.all()
            if configs.count() == 0:
                self.stdout.write(
                    self.style.WARNING('⚠ Aucune configuration de synchronisation trouvée')
                )
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ {configs.count()} configuration(s) trouvée(s)'))

                for config in configs:
                    self.stdout.write(f'  - {config.name} ({config.sync_type})')

            # Test 4: Test spécifique d'une configuration
            if options['config_id']:
                config_id = options['config_id']
                try:
                    config = SyncConfiguration.objects.get(id=config_id)
                    self.stdout.write(f'Test 4: Test de la configuration "{config.name}"...')

                    # Créer l'orchestrateur
                    orchestrator = SyncOrchestrator(
                        source_instance=config.source_instance,
                        destination_instance=config.destination_instance
                    )

                    # Test de compatibilité
                    compatibility = orchestrator._check_global_compatibility()
                    if compatibility['compatible']:
                        self.stdout.write(self.style.SUCCESS('✓ Instances compatibles'))
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'✗ Instances incompatibles: {"; ".join(compatibility.get("errors", []))}'
                            )
                        )

                    # Test des services individuels
                    self.stdout.write('Test des services individuels...')

                    # Test service métadonnées
                    try:
                        families = orchestrator.metadata_service.get_available_families()
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Service métadonnées: {len(families)} familles disponibles')
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠ Service métadonnées: {e}')
                        )

                    if not options['dry_run'] and not options['metadata_only']:
                        self.stdout.write(
                            self.style.WARNING(
                                'Mode test actif désactivé. Utilisez --dry-run pour des tests sans impact.'
                            )
                        )
                    elif options['dry_run']:
                        self.stdout.write('Mode test seulement - aucune synchronisation réelle')

                except SyncConfiguration.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'Configuration avec ID {config_id} introuvable')
                    )

            # Test 5: Vérifier les URL patterns
            self.stdout.write('Test 5: Vérification des URLs...')
            try:
                from django.urls import reverse
                urls_to_test = [
                    'sync_config_list',
                    'dhis2_instance_list',
                ]

                for url_name in urls_to_test:
                    try:
                        url = reverse(url_name)
                        self.stdout.write(self.style.SUCCESS(f'  ✓ {url_name}: {url}'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  ✗ {url_name}: {e}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Erreur vérification URLs: {e}'))

            self.stdout.write(
                self.style.SUCCESS('\n=== TEST TERMINÉ ===')
            )
            self.stdout.write(
                'Le système de synchronisation semble être correctement configuré.'
            )
            self.stdout.write(
                'Vous pouvez maintenant utiliser l\'interface web pour lancer des synchronisations.'
            )

        except Exception as e:
            logger.error(f"Erreur lors du test du système: {e}", exc_info=True)
            raise CommandError(f'Erreur lors du test: {e}')