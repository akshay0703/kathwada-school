import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Role, User


class Command(BaseCommand):
    """
    Creates (or updates) a single Admin superuser from two environment
    variables: DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD.

    Exists specifically because Render's free Web Service plan has no Shell
    access, so `python manage.py createsuperuser` (interactive) cannot be
    run there. This command is safe to run on every deploy (via build.sh):
    - If the env vars aren't set, it does nothing and exits quietly.
    - If the user doesn't exist yet, it creates them as Admin + superuser.
    - If the user already exists, it leaves them untouched (does NOT reset
      the password on every deploy) and just confirms they're still Admin.
    """

    help = "Idempotently create the first Admin superuser from DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD env vars."

    @transaction.atomic
    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not email or not password:
            self.stdout.write("DJANGO_SUPERUSER_EMAIL/PASSWORD not set — skipping superuser creation.")
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(f"Superuser '{email}' already exists — leaving as-is (password not reset).")
            return

        admin_role, _ = Role.objects.get_or_create(name="Admin")
        User.objects.create_superuser(email=email, password=password, role=admin_role)
        self.stdout.write(self.style.SUCCESS(f"Created superuser '{email}' with Admin role."))
