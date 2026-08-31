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
    - If the user already exists, it leaves them untouched by default (does
      NOT reset the password on every deploy) and just confirms they're
      still Admin.

    Password recovery (opt-in only): if the user already exists AND the
    separate env var DJANGO_SUPERUSER_RESET_PASSWORD is set to "true", the
    password is reset to whatever DJANGO_SUPERUSER_PASSWORD currently holds.
    This is deliberately a second, separate flag — not a side effect of
    changing DJANGO_SUPERUSER_PASSWORD alone — so an accidental password
    edit in Render's dashboard can never silently reset a live account.
    IMPORTANT: remove DJANGO_SUPERUSER_RESET_PASSWORD from Render once the
    reset is confirmed working, otherwise every future deploy will keep
    resetting the password back to this same value — including clobbering
    any password change made later through the ERP's own account settings,
    once that self-service feature exists.
    """

    help = "Idempotently create the first Admin superuser from DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD env vars."

    @transaction.atomic
    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        reset_requested = os.environ.get("DJANGO_SUPERUSER_RESET_PASSWORD", "").lower() == "true"

        if not email or not password:
            self.stdout.write("DJANGO_SUPERUSER_EMAIL/PASSWORD not set — skipping superuser creation.")
            return

        existing = User.objects.filter(email=email).first()
        if existing:
            if reset_requested:
                existing.set_password(password)
                existing.is_superuser = True
                existing.is_staff = True
                existing.is_active = True
                existing.save()
                self.stdout.write(
                    self.style.WARNING(
                        f"DJANGO_SUPERUSER_RESET_PASSWORD=true — password for '{email}' was reset. "
                        "Remove that env var now to prevent future deploys from resetting it again."
                    )
                )
            else:
                self.stdout.write(f"Superuser '{email}' already exists — leaving as-is (password not reset).")
            return

        admin_role, _ = Role.objects.get_or_create(name="Admin")
        User.objects.create_superuser(email=email, password=password, role=admin_role)
        self.stdout.write(self.style.SUCCESS(f"Created superuser '{email}' with Admin role."))
