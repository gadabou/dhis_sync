"""
Management command to stop automatic synchronization

Usage:
    python manage.py stop_auto_sync [config_id]

Examples:
    python manage.py stop_auto_sync          # Stop all running auto-sync threads
    python manage.py stop_auto_sync 1        # Stop specific config by ID
"""

from django.core.management.base import BaseCommand, CommandError
from dhis_app.models import SyncConfiguration
from dhis_app.services.auto_sync.scheduler import stop_auto_sync, get_auto_sync_status
import time


class Command(BaseCommand):
    help = 'Stop automatic synchronization for DHIS2 configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            'config_id',
            nargs='?',
            type=int,
            help='ID of the sync configuration to stop (optional, stops all if not provided)'
        )

    def handle(self, *args, **options):
        config_id = options.get('config_id')

        try:
            if config_id:
                self.stop_specific_config(config_id)
            else:
                self.stop_all_configs()
        except Exception as e:
            raise CommandError(f'Error stopping auto-sync: {e}')

    def stop_specific_config(self, config_id):
        """Stop auto-sync for a specific configuration"""
        # Check if it's running
        status = get_auto_sync_status(config_id)

        if not status['is_running']:
            self.stdout.write(self.style.WARNING(
                f'Auto-sync for configuration {config_id} is not running.'
            ))
            return

        try:
            config = SyncConfiguration.objects.get(id=config_id)
            config_name = config.name
        except SyncConfiguration.DoesNotExist:
            config_name = f'ID {config_id}'

        self.stdout.write(f'Stopping auto-sync for: {config_name}...')

        stop_auto_sync(config_id)

        # Wait and verify
        time.sleep(2)
        status = get_auto_sync_status(config_id)

        if not status['is_running']:
            self.stdout.write(self.style.SUCCESS(
                f'✓ Auto-sync stopped successfully for "{config_name}"'
            ))
        else:
            raise CommandError('Failed to stop auto-sync. Check logs for details.')

    def stop_all_configs(self):
        """Stop auto-sync for all running configurations"""
        # Get current status
        status = get_auto_sync_status()

        if status['total_active'] == 0:
            self.stdout.write(self.style.WARNING(
                'No auto-sync threads currently running.'
            ))
            return

        self.stdout.write(f'Stopping {status["total_active"]} auto-sync thread(s)...\n')

        for config_status in status['active_configs']:
            try:
                config = SyncConfiguration.objects.get(id=config_status['config_id'])
                self.stdout.write(f'  - Stopping: {config.name}')
            except SyncConfiguration.DoesNotExist:
                self.stdout.write(f'  - Stopping: Config ID {config_status["config_id"]}')

        stop_auto_sync()  # Stop all

        # Wait and verify
        time.sleep(2)
        status = get_auto_sync_status()

        if status['total_active'] == 0:
            self.stdout.write(self.style.SUCCESS(
                '\n✓ All auto-sync threads stopped successfully'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'\n⚠ {status["total_active"]} thread(s) still running. They may take time to stop.'
            ))