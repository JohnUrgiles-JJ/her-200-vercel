"""
Create a superuser from env vars, once. Safe to run on every deploy.

    DJANGO_SUPERUSER_EMAIL=admin@example.com DJANGO_SUPERUSER_PASSWORD=... python manage.py ensure_superuser

- Does nothing (exit 0) if either variable is missing or empty.
- Does nothing (exit 0) if a user with that email (as username) already exists.
  It never changes an existing user's password.
- The email is lowercased and used as both username and email, like the rest of the app.
"""

import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser from DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD if it doesn't exist."

    def handle(self, *args, **options):
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip().lower()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "")

        if not email or not password:
            self.stdout.write("ensure_superuser: DJANGO_SUPERUSER_EMAIL/PASSWORD not set, skipping.")
            return

        if User.objects.filter(username__iexact=email).exists():
            self.stdout.write(f"ensure_superuser: user {email} already exists, skipping.")
            return

        User.objects.create_superuser(username=email, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"ensure_superuser: created superuser {email}."))
