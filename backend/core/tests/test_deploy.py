"""Tests for the deployment helpers: /api/health/ and the ensure_superuser command."""

import os
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import OperationalError
from django.test import TestCase
from rest_framework.test import APIClient


class HealthCheckTests(TestCase):
    def test_health_ok_without_auth(self):
        response = APIClient().get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "db": True})

    def test_health_ignores_bad_token(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")
        self.assertEqual(client.get("/api/health/").status_code, 200)

    def test_health_reports_db_failure_with_200(self):
        with mock.patch("core.views.connection.cursor", side_effect=OperationalError("down")):
            with self.assertLogs("core.views", level="ERROR"):
                response = APIClient().get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "db": False})


class EnsureSuperuserTests(TestCase):
    def run_command(self, **env):
        out = StringIO()
        with mock.patch.dict(os.environ, env):
            call_command("ensure_superuser", stdout=out)
        return out.getvalue()

    def test_skips_when_vars_missing(self):
        output = self.run_command(DJANGO_SUPERUSER_EMAIL="", DJANGO_SUPERUSER_PASSWORD="")
        self.assertIn("skipping", output)
        self.assertFalse(User.objects.filter(is_superuser=True).exists())

    def test_skips_when_only_email_set(self):
        self.run_command(DJANGO_SUPERUSER_EMAIL="admin@example.com", DJANGO_SUPERUSER_PASSWORD="")
        self.assertFalse(User.objects.exists())

    def test_creates_superuser_with_email_as_username(self):
        self.run_command(DJANGO_SUPERUSER_EMAIL=" Admin@Example.com ", DJANGO_SUPERUSER_PASSWORD="s3cret-pass")
        user = User.objects.get()
        self.assertEqual(user.username, "admin@example.com")
        self.assertEqual(user.email, "admin@example.com")
        self.assertTrue(user.is_superuser and user.is_staff)
        self.assertTrue(user.check_password("s3cret-pass"))

    def test_existing_user_is_left_alone(self):
        User.objects.create_user(username="admin@example.com", email="admin@example.com", password="original")
        output = self.run_command(DJANGO_SUPERUSER_EMAIL="admin@example.com", DJANGO_SUPERUSER_PASSWORD="new-pass")
        self.assertIn("already exists", output)
        user = User.objects.get()
        self.assertTrue(user.check_password("original"))
        self.assertFalse(user.is_superuser)
