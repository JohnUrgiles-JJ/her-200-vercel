"""Phase 6: email notifications to matched mentors (core.notify.email_mentor and friends).

Everything uses Django's locmem backend, so emails land in django.core.mail.outbox. Most tests set
NOTIFY_EMAILS_SYNC=True so the emails are sent inline (no thread timing). The thread tests join the thread.
"""

import os
import smtplib
import threading
from io import StringIO
from unittest import mock

from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from core import notify
from core.models import Question, QuestionMatch
from core.tests.test_questions import FAST_HASHER, NO_LLM, UX_QUESTION, client_for, make_mentors, make_user

SUBJECT = "A student has a question for you on ConnectHER"
FRONTEND = "https://connecther.example"
INBOX = f"{FRONTEND}/inbox"
LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


def html_part(message):
    [(content, mimetype)] = message.alternatives
    assert mimetype == "text/html"
    return content


@mock.patch.dict(os.environ, NO_LLM)
@FAST_HASHER
@override_settings(EMAIL_BACKEND=LOCMEM, NOTIFY_EMAILS_SYNC=True, FRONTEND_URL=FRONTEND)
class MentorEmailTests(TestCase):
    def setUp(self):
        self.mentors = make_mentors()
        self.mentee, token = make_user("maria@t.com", "Maria Lopez", "mentee")
        self.client = client_for(token)
        self.fake = [
            {"mentor_id": self.mentors["maya"].id, "reason": "Switched into UX from teaching"},
            {"mentor_id": self.mentors["sofia"].id, "reason": "First-gen and broke in anyway"},
            {"mentor_id": self.mentors["priya"].id, "reason": "Built a portfolio from research"},
        ]
        # The WebSocket push is Phase 5's job and is tested there.
        patcher = mock.patch("core.notify.push", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def ask(self, text=UX_QUESTION):
        with mock.patch("core.views.matching.match_mentors", return_value=self.fake):
            with self.captureOnCommitCallbacks(execute=True):
                res = self.client.post("/api/questions/", {"text": text}, format="json")
        self.assertEqual(res.status_code, 201)
        return res

    # --- through the API ------------------------------------------------------------------------------

    def test_asking_sends_one_email_per_matched_mentor(self):
        self.ask()
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual([m.to for m in mail.outbox], [["maya@t.com"], ["sofia@t.com"], ["priya@t.com"]])
        for message in mail.outbox:
            self.assertEqual(message.subject, SUBJECT)
            self.assertIn(f"Answer it here: {INBOX}", message.body)
            self.assertIn(f'href="{INBOX}"', html_part(message))

    def test_email_content(self):
        self.ask()
        maya = mail.outbox[0]
        self.assertTrue(maya.body.startswith("Hi Maya,\n"))
        self.assertIn(f'"{UX_QUESTION}"', maya.body)
        self.assertIn("Why you were matched: Switched into UX from teaching", maya.body)
        self.assertIn("signed up to answer questions about your experience", maya.body)
        self.assertTrue(maya.body.rstrip().endswith("— The ConnectHER team"))
        self.assertEqual(maya.from_email, "ConnectHER <noreply@connecther.local>")

        page = html_part(maya)
        self.assertIn("Hi Maya,", page)
        self.assertIn(UX_QUESTION, page)
        self.assertIn("#7c3aed", page)
        self.assertIn("Answer in your inbox", page)
        self.assertIn("Switched into UX from teaching", page)
        self.assertNotIn("<style", page)  # inline styles only

        self.assertTrue(mail.outbox[1].body.startswith("Hi Sofia,\n"))
        self.assertIn("Why you were matched: First-gen and broke in anyway", mail.outbox[1].body)

    def test_html_escapes_user_text(self):
        self.ask("<script>alert(1)</script> How do I get into UX & research?")
        page = html_part(mail.outbox[0])
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; How do I get into UX &amp; research?", page)

    def test_no_matches_sends_nothing(self):
        self.fake = []
        self.ask()
        self.assertEqual(mail.outbox, [])

    def test_mentor_without_email_is_skipped_others_still_sent(self):
        self.mentors["sofia"].email = ""
        self.mentors["sofia"].save()
        self.ask()
        self.assertEqual([m.to for m in mail.outbox], [["maya@t.com"], ["priya@t.com"]])

    def test_one_failing_send_does_not_stop_the_others_or_the_request(self):
        real_send = EmailMultiAlternatives.send

        def send(message, *args, **kwargs):
            if message.to == ["sofia@t.com"]:
                raise smtplib.SMTPServerDisconnected("Gmail hung up")
            return real_send(message, *args, **kwargs)

        with mock.patch.object(EmailMultiAlternatives, "send", autospec=True, side_effect=send):
            with self.assertLogs("core.notify", level="ERROR") as logs:
                res = self.ask()
        self.assertEqual(len(res.data["matches"]), 3)
        self.assertEqual([m.to for m in mail.outbox], [["maya@t.com"], ["priya@t.com"]])
        self.assertTrue(any("Gmail hung up" in line for line in logs.output))

    def test_query_failure_while_gathering_does_not_fail_request(self):
        with mock.patch("core.notify.User.objects.select_related", side_effect=RuntimeError("db down")):
            with self.assertLogs("core.notify", level="ERROR"):
                self.ask()
        self.assertEqual(mail.outbox, [])
        self.assertEqual(Question.objects.count(), 1)

    # --- email_mentor directly ------------------------------------------------------------------------

    def test_email_mentor_with_a_saved_match(self):
        self.ask()
        mail.outbox.clear()
        match = QuestionMatch.objects.get(rank=1)
        self.assertTrue(notify.email_mentor(match))
        [message] = mail.outbox
        self.assertEqual(message.to, ["maya@t.com"])
        self.assertEqual(message.subject, SUBJECT)
        self.assertIn(INBOX, message.body)

    def test_email_mentor_skips_empty_address(self):
        job = notify.MentorEmail(to="", first_name="Maya", question=UX_QUESTION, reason="r")
        self.assertFalse(notify.email_mentor(job))
        self.assertEqual(mail.outbox, [])

    def test_exception_inside_send_does_not_raise(self):
        job = notify.MentorEmail(to="maya@t.com", first_name="Maya", question=UX_QUESTION, reason="r", match_id=7)
        with mock.patch.object(EmailMultiAlternatives, "send", side_effect=smtplib.SMTPAuthenticationError(535, b"no")):
            with self.assertLogs("core.notify", level="ERROR") as logs:
                result = notify.email_mentor(job)
        self.assertFalse(result)
        self.assertIn("match 7", logs.output[0])

    def test_exception_while_building_does_not_raise(self):
        job = notify.MentorEmail(to="maya@t.com", first_name="Maya", question=UX_QUESTION, reason="r")
        with mock.patch("core.notify.mentor_email_html", side_effect=ValueError("template bug")):
            with self.assertLogs("core.notify", level="ERROR"):
                self.assertFalse(notify.email_mentor(job))
        self.assertFalse(notify.email_mentor(object()))  # not a match at all: logged, False, no raise


@mock.patch.dict(os.environ, NO_LLM)
@FAST_HASHER
@override_settings(EMAIL_BACKEND=LOCMEM, NOTIFY_EMAILS_SYNC=False, FRONTEND_URL=FRONTEND)
class BackgroundThreadTests(TestCase):
    """The real (non-test) path: emails go out on a daemon thread after the response."""

    def setUp(self):
        self.mentors = make_mentors()
        self.mentee, token = make_user("maria@t.com", "Maria Lopez", "mentee")
        self.client = client_for(token)
        patcher = mock.patch("core.notify.push", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_thread_gets_plain_values_and_sends_all_emails(self):
        fake = [{"mentor_id": self.mentors[n].id, "reason": f"reason {n}"} for n in ("maya", "amara")]
        threads = []
        real_start = notify.start_mentor_emails

        def start(jobs):
            jobs = list(jobs)
            for job in jobs:  # no model instances or querysets cross the thread boundary
                self.assertIsInstance(job, notify.MentorEmail)
                for value in vars(job).values():
                    self.assertIsInstance(value, (str, int))
            thread = real_start(jobs)
            threads.append(thread)
            return thread

        with mock.patch("core.notify.start_mentor_emails", side_effect=start):
            with mock.patch("core.views.matching.match_mentors", return_value=fake):
                with self.captureOnCommitCallbacks(execute=True):
                    res = self.client.post("/api/questions/", {"text": UX_QUESTION}, format="json")
        self.assertEqual(res.status_code, 201)

        [thread] = threads
        self.assertIsInstance(thread, threading.Thread)
        self.assertTrue(thread.daemon)
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["amara@t.com", "maya@t.com"])

    def test_slow_smtp_does_not_block_the_response(self):
        release = threading.Event()
        started = threading.Event()

        def slow_send(*args, **kwargs):
            started.set()
            release.wait(timeout=5)
            return 1

        fake = [{"mentor_id": self.mentors["maya"].id, "reason": "r"}]
        with mock.patch.object(EmailMultiAlternatives, "send", side_effect=slow_send), \
                mock.patch("core.notify.connection") as conn:
            with mock.patch("core.views.matching.match_mentors", return_value=fake):
                with self.captureOnCommitCallbacks(execute=True):
                    res = self.client.post("/api/questions/", {"text": UX_QUESTION}, format="json")
            # The response is back while the email is still "sending".
            self.assertEqual(res.status_code, 201)
            self.assertTrue(started.wait(timeout=5))
            self.assertFalse(release.is_set())
            release.set()
            for t in threading.enumerate():
                if t.name == "mentor-emails":
                    t.join(timeout=5)
            conn.close.assert_called_once()  # the thread closes its DB connection at the end

    def test_thread_closes_connection_even_if_everything_fails(self):
        job = notify.MentorEmail(to="maya@t.com", first_name="Maya", question=UX_QUESTION, reason="r")
        with mock.patch("core.notify.email_mentor", side_effect=RuntimeError("boom")), \
                mock.patch("core.notify.connection") as conn:
            with self.assertRaises(RuntimeError):  # email_mentor never raises in reality; check the finally
                notify.send_mentor_emails([job])
        conn.close.assert_called_once()

    def test_nothing_to_send_starts_no_thread(self):
        self.assertIsNone(notify.start_mentor_emails([]))


@override_settings(EMAIL_BACKEND=LOCMEM, FRONTEND_URL=FRONTEND)
class TestEmailCommandTests(TestCase):
    def test_sends_a_sample_email(self):
        out = StringIO()
        call_command("test_email", "teammate@example.com", stdout=out)
        [message] = mail.outbox
        self.assertEqual(message.to, ["teammate@example.com"])
        self.assertEqual(message.subject, SUBJECT)
        self.assertIn(INBOX, message.body)
        self.assertIn("Sent", out.getvalue())

    def test_invalid_address(self):
        with self.assertRaises(CommandError):
            call_command("test_email", "not-an-email", stdout=StringIO())
        self.assertEqual(mail.outbox, [])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST_USER="", EMAIL_HOST_PASSWORD=""
    )
    def test_smtp_without_credentials_fails_clearly(self):
        with self.assertRaisesMessage(CommandError, "EMAIL_HOST_USER and EMAIL_HOST_PASSWORD"):
            call_command("test_email", "teammate@example.com", stdout=StringIO())

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST_USER="team@gmail.com", EMAIL_HOST_PASSWORD="wrongwrongwrongw",
    )
    def test_gmail_auth_error_gives_app_password_hint(self):
        with mock.patch.object(EmailMultiAlternatives, "send", side_effect=smtplib.SMTPAuthenticationError(535, b"bad")):
            with self.assertRaisesMessage(CommandError, "App Password"):
                call_command("test_email", "teammate@example.com", stdout=StringIO())
