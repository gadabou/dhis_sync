from django.core.management.base import BaseCommand
from dhis_app.models import DHIS2Instance


class Command(BaseCommand):
    help = 'Nettoie les URLs des instances DHIS2 pour éviter les doubles slashes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche les modifications sans les appliquer',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        instances = DHIS2Instance.objects.all()
        modified_count = 0

        self.stdout.write(self.style.SUCCESS(f'Vérification de {instances.count()} instances...'))

        for instance in instances:
            original_url = instance.base_url

            if original_url:
                # Nettoyer l'URL
                cleaned_url = original_url.rstrip('/') + '/'

                if original_url != cleaned_url:
                    modified_count += 1

                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'[DRY RUN] Instance "{instance.name}": '
                                f'"{original_url}" -> "{cleaned_url}"'
                            )
                        )
                    else:
                        instance.base_url = cleaned_url
                        instance.save(update_fields=['base_url'])

                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Instance "{instance.name}" mise à jour: '
                                f'"{original_url}" -> "{cleaned_url}"'
                            )
                        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] {modified_count} instances nécessitent une modification'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'{modified_count} instances ont été mises à jour'
                )
            )