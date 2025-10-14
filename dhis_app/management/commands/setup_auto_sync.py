"""
Management command to setup auto-sync settings for a configuration

Usage:
    python manage.py setup_auto_sync <config_id> [options]

Examples:
    python manage.py setup_auto_sync 3
    python manage.py setup_auto_sync 3 --interval 600 --no-immediate
"""

from django.core.management.base import BaseCommand, CommandError
from dhis_app.models import SyncConfiguration, AutoSyncSettings


class Command(BaseCommand):
    help = 'Setup auto-sync settings for a sync configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            'config_id',
            type=int,
            help='ID of the sync configuration'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=300,
            help='Check interval in seconds (default: 300 = 5 minutes)'
        )
        parser.add_argument(
            '--immediate',
            action='store_true',
            default=True,
            help='Sync immediately when changes are detected (default: True)'
        )
        parser.add_argument(
            '--no-immediate',
            dest='immediate',
            action='store_false',
            help='Wait before syncing (uses --delay)'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=30,
            help='Delay before sync in seconds (default: 30, used with --no-immediate)'
        )
        parser.add_argument(
            '--metadata-only',
            action='store_true',
            help='Monitor only metadata changes'
        )
        parser.add_argument(
            '--data-only',
            action='store_true',
            help='Monitor only data changes'
        )
        parser.add_argument(
            '--max-per-hour',
            type=int,
            default=10,
            help='Maximum syncs per hour (default: 10)'
        )
        parser.add_argument(
            '--cooldown',
            type=int,
            default=1800,
            help='Cooldown after error in seconds (default: 1800 = 30 minutes)'
        )
        parser.add_argument(
            '--enable',
            action='store_true',
            default=True,
            help='Enable auto-sync (default: True)'
        )
        parser.add_argument(
            '--disable',
            dest='enable',
            action='store_false',
            help='Create settings but keep auto-sync disabled'
        )

    def handle(self, *args, **options):
        config_id = options['config_id']

        # Get the configuration
        try:
            config = SyncConfiguration.objects.get(id=config_id)
        except SyncConfiguration.DoesNotExist:
            raise CommandError(f'Configuration with ID {config_id} not found.')

        self.stdout.write(f'\nConfiguration: {config.name} (ID: {config_id})')
        self.stdout.write(f'  Source: {config.source_instance.name}')
        self.stdout.write(f'  Target: {config.destination_instance.name}')
        self.stdout.write(f'  Mode: {config.execution_mode}')

        # Check if already has auto-sync settings
        try:
            auto_settings = config.auto_sync_settings
            self.stdout.write(self.style.WARNING(
                f'\n⚠ Configuration already has auto-sync settings!'
            ))
            self.stdout.write(f'  Enabled: {auto_settings.is_enabled}')
            self.stdout.write(f'  Interval: {auto_settings.check_interval}s')

            if not self.confirm_action('Do you want to update these settings?'):
                self.stdout.write(self.style.WARNING('Aborted.'))
                return

            # Update existing settings
            auto_settings.is_enabled = options['enable']
            auto_settings.check_interval = options['interval']
            auto_settings.immediate_sync = options['immediate']
            auto_settings.delay_before_sync = options['delay']
            auto_settings.monitor_metadata = not options['data_only']
            auto_settings.monitor_data_values = not options['metadata_only']
            auto_settings.max_sync_per_hour = options['max_per_hour']
            auto_settings.cooldown_after_error = options['cooldown']
            auto_settings.save()

            self.stdout.write(self.style.SUCCESS(
                '\n✓ Auto-sync settings updated successfully!'
            ))

        except AutoSyncSettings.DoesNotExist:
            # Create new settings
            auto_settings = AutoSyncSettings.objects.create(
                sync_config=config,
                is_enabled=options['enable'],
                check_interval=options['interval'],
                immediate_sync=options['immediate'],
                delay_before_sync=options['delay'],
                monitor_metadata=not options['data_only'],
                monitor_data_values=not options['metadata_only'],
                max_sync_per_hour=options['max_per_hour'],
                cooldown_after_error=options['cooldown'],
                notify_on_change=False,
                notify_on_sync_complete=False
            )

            self.stdout.write(self.style.SUCCESS(
                '\n✓ Auto-sync settings created successfully!'
            ))

        # Display settings
        self.stdout.write('\n=== Auto-Sync Settings ===')
        self.stdout.write(f'  Enabled: {auto_settings.is_enabled}')
        self.stdout.write(f'  Check interval: {auto_settings.check_interval}s ({auto_settings.check_interval // 60} minutes)')
        self.stdout.write(f'  Immediate sync: {auto_settings.immediate_sync}')
        if not auto_settings.immediate_sync:
            self.stdout.write(f'  Delay before sync: {auto_settings.delay_before_sync}s')
        self.stdout.write(f'  Monitor metadata: {auto_settings.monitor_metadata}')
        self.stdout.write(f'  Monitor data: {auto_settings.monitor_data_values}')
        self.stdout.write(f'  Max syncs per hour: {auto_settings.max_sync_per_hour}')
        self.stdout.write(f'  Cooldown after error: {auto_settings.cooldown_after_error}s ({auto_settings.cooldown_after_error // 60} minutes)')

        # Suggest next steps
        if config.execution_mode != 'automatic':
            self.stdout.write(self.style.WARNING(
                f'\n⚠ Note: Configuration mode is "{config.execution_mode}"'
            ))
            self.stdout.write('  Change to "automatic" to use auto-sync')

        if not config.is_active:
            self.stdout.write(self.style.WARNING(
                '\n⚠ Note: Configuration is not active'
            ))
            self.stdout.write('  Activate it to start auto-sync')

        if auto_settings.is_enabled and config.execution_mode == 'automatic' and config.is_active:
            self.stdout.write(self.style.SUCCESS(
                '\n✓ Configuration is ready for auto-sync!'
            ))
            self.stdout.write('\nTo start auto-sync:')
            self.stdout.write(f'  python manage.py start_auto_sync {config_id}')
            self.stdout.write('\nOr start all active configs:')
            self.stdout.write('  python manage.py start_auto_sync')

    def confirm_action(self, message):
        """Ask for user confirmation"""
        response = input(f'{message} [y/N]: ').lower().strip()
        return response == 'y'