# myloan/management/commands/createsuperuser.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser with username and password only'

    def add_arguments(self, parser):
        parser.add_argument('--username', help="Superuser's username")
        parser.add_argument('--password', help="Superuser's password")

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']

        if not username or not password:
            self.stdout.write(self.style.ERROR('Both --username and --password are required'))
            return

        User.objects.create_superuser(
            username=username,
            password=password
        )
        self.stdout.write(self.style.SUCCESS('Superuser created successfully'))