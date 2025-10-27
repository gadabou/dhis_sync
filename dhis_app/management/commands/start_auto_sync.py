"""
Management command to start automatic synchronization

Usage:
    python manage.py start_auto_sync [config_id]

Examples:
    python manage.py start_auto_sync          # Start all active automatic configs
    python manage.py start_auto_sync 1        # Start specific config by ID
"""

from django.core.management.base import BaseCommand, CommandError
from dhis_app.models import SyncConfiguration, AutoSyncSettings
from dhis_app.services.auto_sync.scheduler import start_auto_sync, get_auto_sync_status
import time


class Command(BaseCommand):
    help = 'Start automatic synchronization for DHIS2 configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            'config_id',
            nargs='?',
            type=int,
            help='ID of the sync configuration to start (optional, starts all if not provided)'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all automatic sync configurations'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show status of running auto-sync threads'
        )

    def handle(self, *args, **options):
        # Handle --list option
        if options['list']:
            self.list_configurations()
            return

        # Handle --status option
        if options['status']:
            self.show_status()
            return

        config_id = options.get('config_id')

        # Start auto-sync
        try:
            if config_id:
                self.start_specific_config(config_id)
            else:
                self.start_all_configs()
        except Exception as e:
            raise CommandError(f'Error starting auto-sync: {e}')

    def list_configurations(self):
        """List all automatic sync configurations"""
        self.stdout.write(self.style.SUCCESS('\n=== Automatic Sync Configurations ===\n'))

        configs = SyncConfiguration.objects.filter(execution_mode='automatic')

        if not configs.exists():
            self.stdout.write(self.style.WARNING('No automatic sync configurations found.'))
            self.stdout.write('Create one with execution_mode="automatic" first.')
            return

        for config in configs:
            self.stdout.write(f'\nConfig ID: {config.id}')
            self.stdout.write(f'  Name: {config.name}')
            self.stdout.write(f'  Source: {config.source_instance.name}')
            self.stdout.write(f'  Target: {config.destination_instance.name}')
            self.stdout.write(f'  Active: {config.is_active}')

            try:
                auto_settings = config.auto_sync_settings
                self.stdout.write(f'  Auto-sync enabled: {auto_settings.is_enabled}')
                self.stdout.write(f'  Check interval: {auto_settings.check_interval}s')
            except AutoSyncSettings.DoesNotExist:
                self.stdout.write(self.style.WARNING('  Auto-sync settings: Not configured'))

        self.stdout.write('')

    def show_status(self):
        """Show status of running auto-sync threads"""
        self.stdout.write(self.style.SUCCESS('\n=== Auto-Sync Status ===\n'))

        status = get_auto_sync_status()

        if status['total_active'] == 0:
            self.stdout.write(self.style.WARNING('No auto-sync threads currently running.'))
            self.stdout.write('Use: python manage.py start_auto_sync')
        else:
            self.stdout.write(f'Total active threads: {status["total_active"]}\n')

            for config_status in status['active_configs']:
                self.stdout.write(f'Config ID: {config_status["config_id"]}')
                self.stdout.write(f'  Thread: {config_status["thread_name"]}')
                self.stdout.write(f'  Status: {self.style.SUCCESS("Running")}\n')

    def start_specific_config(self, config_id):
        """Start auto-sync for a specific configuration"""
        try:
            config = SyncConfiguration.objects.get(id=config_id)
        except SyncConfiguration.DoesNotExist:
            raise CommandError(f'Configuration with ID {config_id} not found.')

        if config.execution_mode != 'automatic':
            raise CommandError(
                f'Configuration "{config.name}" is not in automatic mode. '
                f'Current mode: {config.execution_mode}'
            )

        if not config.is_active:
            raise CommandError(
                f'Configuration "{config.name}" is not active. '
                'Activate it first in the admin interface.'
            )

        try:
            auto_settings = config.auto_sync_settings
        except AutoSyncSettings.DoesNotExist:
            raise CommandError(
                f'Configuration "{config.name}" has no auto-sync settings. '
                'Configure auto-sync settings first.'
            )

        if not auto_settings.is_enabled:
            raise CommandError(
                f'Auto-sync is disabled for "{config.name}". '
                'Enable it in the auto-sync settings.'
            )

        self.stdout.write(f'Starting auto-sync for: {config.name} (ID: {config_id})')
        self.stdout.write(f'  Check interval: {auto_settings.check_interval}s')
        self.stdout.write(f'  Monitor metadata: {auto_settings.monitor_metadata}')
        self.stdout.write(f'  Monitor data: {auto_settings.monitor_data_values}')

        start_auto_sync(config_id)

        # Wait a bit and check if it started successfully
        time.sleep(2)
        status = get_auto_sync_status(config_id)

        if status['is_running']:
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Auto-sync started successfully for "{config.name}"'
            ))
            self.stdout.write(f'Thread: {status["thread_name"]}')
            self.stdout.write('\nMonitoring for changes...')
            self.stdout.write('Press Ctrl+C to stop the management command (auto-sync will continue in background)')
            self.stdout.write('Or use: python manage.py stop_auto_sync {}'.format(config_id))
        else:
            raise CommandError('Failed to start auto-sync. Check logs for details.')

    def start_all_configs(self):
        """Start auto-sync for all eligible configurations"""
        configs = SyncConfiguration.objects.filter(
            execution_mode='automatic',
            is_active=True
        )

        if not configs.exists():
            self.stdout.write(self.style.WARNING(
                'No active automatic sync configurations found.'
            ))
            self.stdout.write('Create one with execution_mode="automatic" first.')
            return

        # Filter configs with enabled auto-sync settings
        eligible_configs = []
        for config in configs:
            try:
                auto_settings = config.auto_sync_settings
                if auto_settings.is_enabled:
                    eligible_configs.append(config)
            except AutoSyncSettings.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'Skipping "{config.name}": No auto-sync settings configured'
                ))

        if not eligible_configs:
            self.stdout.write(self.style.WARNING(
                'No configurations with enabled auto-sync found.'
            ))
            return

        self.stdout.write(f'Starting auto-sync for {len(eligible_configs)} configuration(s):\n')

        for config in eligible_configs:
            self.stdout.write(f'  - {config.name} (ID: {config.id})')

        start_auto_sync()  # Start all

        # Wait and verify
        time.sleep(2)
        status = get_auto_sync_status()

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Started {status["total_active"]} auto-sync thread(s)'
        ))

        if status['active_configs']:
            self.stdout.write('\nActive threads:')
            for config_status in status['active_configs']:
                config = SyncConfiguration.objects.get(id=config_status['config_id'])
                self.stdout.write(f'  - {config.name}: {config_status["thread_name"]}')

        self.stdout.write('\nMonitoring for changes...')
        self.stdout.write('Press Ctrl+C to stop the management command (auto-sync will continue in background)')
        self.stdout.write('Or use: python manage.py stop_auto_sync')