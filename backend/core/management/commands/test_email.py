"""
Send one sample "new question" mentor email, to check the email setup in a few seconds.

    python manage.py test_email you@example.com

It uses the real EMAIL_BACKEND from settings (console by default, Gmail SMTP when configured) and the same
builder as the real notification (core.notify.build_mentor_email). Unlike email_mentor(), it does NOT swallow
errors: a failure prints the reason and a hint, and the command exits non-zero.
"""

import smtplib
import socket

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from core.notify import MENTOR_EMAIL_SUBJECT, MentorEmail, build_mentor_email, inbox_url

SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


class Command(BaseCommand):
    help = "Send a sample mentor notification email to <to_address> using the configured EMAIL_BACKEND."

    def add_arguments(self, parser):
        parser.add_argument("to_address", help="Where to send the sample email.")

    def handle(self, *args, **options):
        to = options["to_address"].strip()
        try:
            validate_email(to)
        except ValidationError:
            raise CommandError(f"'{to}' is not a valid email address.")

        backend = settings.EMAIL_BACKEND
        is_smtp = backend == SMTP_BACKEND
        self.stdout.write(f"Backend: {backend}")
        if is_smtp:
            self.stdout.write(
                f"SMTP:    {settings.EMAIL_HOST}:{settings.EMAIL_PORT} (TLS={settings.EMAIL_USE_TLS}), "
                f"user={settings.EMAIL_HOST_USER or '(empty)'}, "
                f"password={'set' if settings.EMAIL_HOST_PASSWORD else '(empty)'}, timeout={settings.EMAIL_TIMEOUT}s"
            )
            if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                raise CommandError("EMAIL_HOST_USER and EMAIL_HOST_PASSWORD must both be set in .env for Gmail.")
        else:
            self.stdout.write("(Not SMTP: the email is printed/stored, not delivered. See PROGRESS.md, Phase 6.)")
        self.stdout.write(f"From:    {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"To:      {to}")
        self.stdout.write(f"Subject: {MENTOR_EMAIL_SUBJECT}")
        self.stdout.write(f"Link:    {inbox_url()}")
        self.stdout.write("")

        job = MentorEmail(
            to=to,
            first_name="Maya",
            question="How do I break into UX design without a design degree? I am a teacher right now.",
            reason="Switched into UX from teaching, with no design degree",
        )
        try:
            sent = build_mentor_email(job).send(fail_silently=False)
        except smtplib.SMTPAuthenticationError as exc:
            raise CommandError(
                f"Gmail rejected the login ({exc.smtp_code}). EMAIL_HOST_PASSWORD must be a 16-character "
                "App Password (not your normal password), 2-Step Verification must be on, and EMAIL_HOST_USER "
                "must be the Gmail address that created the App Password."
            )
        except smtplib.SMTPException as exc:  # before OSError: SMTPException subclasses it
            raise CommandError(f"The SMTP server refused the email: {exc!r}")
        except (socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
            raise CommandError(
                f"Couldn't reach {settings.EMAIL_HOST}:{settings.EMAIL_PORT}: {exc!r}. "
                "Check your internet connection; some networks block outbound port 587."
            )
        except Exception as exc:
            raise CommandError(f"Sending failed: {exc!r}")

        if sent != 1:
            raise CommandError(f"The backend reported {sent} emails sent (expected 1).")
        if is_smtp:
            self.stdout.write(self.style.SUCCESS(f"Sent. Check {to} (and its spam folder)."))
        else:
            self.stdout.write(self.style.SUCCESS("Sent to the configured backend (see the output above)."))
