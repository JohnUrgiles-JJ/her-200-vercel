"""Notifications: new questions for matched mentors, new answers for mentees.

Both hooks run via transaction.on_commit (from QuestionCreateView and AnswerCreateView), after the rows
are saved, inside a try/except, so nothing here can fail the request. push() also never raises on its own.

Live delivery (Phase 5) goes over Django Channels to the group f"user_{id}" that each connected socket joins
(core/consumers.py). Event shapes are fixed by Section 3.3 of the plan.

Email (Phase 6) goes to each matched mentor from a background daemon thread, so SMTP never slows the
POST /questions/ response. Everything the thread needs is copied into plain MentorEmail values first.
"""

import html
import logging
import threading
from dataclasses import dataclass

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.db import connection

from .consumers import group_for
from .serializers import _display_name, short_name

logger = logging.getLogger(__name__)


def push(user_id, payload):
    """Send `payload` (a JSON-able dict) to every open socket of user `user_id`. Never raises.

    Returns True if the message was handed to the channel layer (it's silently dropped if the user has no
    open socket), False if sending failed. Call it from sync code only (views, on_commit callbacks).
    """
    try:
        layer = get_channel_layer()
        if layer is None:
            logger.warning("No channel layer configured; dropping %s for user %s", payload.get("event"), user_id)
            return False
        async_to_sync(layer.group_send)(group_for(user_id), {"type": "notify", "payload": payload})
        return True
    except Exception:
        logger.exception("WebSocket push of %s to user %s failed", payload.get("event"), user_id)
        return False


def new_question_event(question, match):
    return {
        "event": "new_question",
        "match_id": match.id,
        "question_id": question.id,
        "question": question.text,
        "reason": match.reason,
        "mentee_name": short_name(question.mentee),
    }


def new_answer_event(answer):
    match = answer.match
    return {
        "event": "new_answer",
        "question_id": match.question_id,
        "match_id": match.id,
        "mentor_name": _display_name(match.mentor),
        "text": answer.text,
    }


# ============================================================================
# EMAIL: new question -> matched mentor (Phase 6)
# ============================================================================
MENTOR_EMAIL_SUBJECT = "A student has a question for you on ConnectHER"
ACCENT = "#7c3aed"


@dataclass(frozen=True)
class MentorEmail:
    """Plain values for one mentor email. Safe to hand to another thread (no model instances, no querysets)."""

    to: str
    first_name: str
    question: str
    reason: str
    match_id: int | None = None
    question_id: int | None = None


def _first_name(user):
    parts = _display_name(user).split()
    return parts[0] if parts else ""


def mentor_email_for(question, match, mentor):
    """A MentorEmail from already-loaded objects. Reads only attributes, so no lazy queries if they're loaded."""
    return MentorEmail(
        to=(mentor.email or "").strip(),
        first_name=_first_name(mentor),
        question=question.text,
        reason=match.reason,
        match_id=match.id,
        question_id=question.id,
    )


def inbox_url():
    return f"{settings.FRONTEND_URL.rstrip('/')}/inbox"


def mentor_email_text(job):
    greeting = f"Hi {job.first_name}," if job.first_name else "Hi,"
    return (
        f"{greeting}\n"
        "\n"
        "A student on ConnectHER asked a question, and you're one of the mentors we matched it to:\n"
        "\n"
        f'"{job.question}"\n'
        "\n"
        f"Why you were matched: {job.reason}\n"
        "\n"
        f"Answer it here: {inbox_url()}\n"
        "\n"
        "You're getting this because you signed up to answer questions about your experience.\n"
        "\n"
        "— The ConnectHER team\n"
    )


def mentor_email_html(job):
    e = html.escape
    greeting = f"Hi {e(job.first_name)}," if job.first_name else "Hi,"
    url = e(inbox_url(), quote=True)
    font = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f5f3ff;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f3ff;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:12px;border-top:4px solid {ACCENT};font-family:{font};color:#1f2937;">
        <tr><td style="padding:28px 28px 8px;">
          <p style="margin:0 0 16px;font-size:13px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:{ACCENT};">ConnectHER</p>
          <p style="margin:0 0 16px;font-size:16px;line-height:1.5;">{greeting}</p>
          <p style="margin:0 0 16px;font-size:16px;line-height:1.5;">A student on ConnectHER asked a question, and you're one of the mentors we matched it to:</p>
          <blockquote style="margin:0 0 16px;padding:12px 16px;border-left:3px solid {ACCENT};background:#faf5ff;font-size:16px;line-height:1.5;font-style:italic;">&ldquo;{e(job.question)}&rdquo;</blockquote>
          <p style="margin:0 0 24px;font-size:15px;line-height:1.5;color:#4b5563;"><strong style="color:#1f2937;">Why you were matched:</strong> {e(job.reason)}</p>
          <p style="margin:0 0 20px;">
            <a href="{url}" style="display:inline-block;background:{ACCENT};color:#ffffff;text-decoration:none;font-weight:600;font-size:15px;padding:12px 22px;border-radius:8px;">Answer in your inbox</a>
          </p>
          <p style="margin:0 0 24px;font-size:13px;line-height:1.5;color:#6b7280;">Or open this link: <a href="{url}" style="color:{ACCENT};">{url}</a></p>
        </td></tr>
        <tr><td style="padding:16px 28px 28px;border-top:1px solid #ede9fe;font-size:13px;line-height:1.5;color:#6b7280;">
          You're getting this because you signed up to answer questions about your experience.<br>
          &mdash; The ConnectHER team
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def build_mentor_email(job):
    """The EmailMultiAlternatives for one MentorEmail (plain text + HTML alternative). Doesn't send."""
    message = EmailMultiAlternatives(
        subject=MENTOR_EMAIL_SUBJECT,
        body=mentor_email_text(job),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[job.to],
    )
    message.attach_alternative(mentor_email_html(job), "text/html")
    return message


def email_mentor(match):
    """Email one matched mentor. Never raises.

    `match` is a saved QuestionMatch (match.mentor and match.question are read, from the DB if not loaded)
    or a ready MentorEmail (what the background thread passes, so it never touches the DB).
    Returns True if the email was handed to the backend, False if skipped (no address) or failed.
    """
    match_id = getattr(match, "match_id", None) or getattr(match, "id", None)
    try:
        job = match if isinstance(match, MentorEmail) else mentor_email_for(match.question, match, match.mentor)
        if not job.to:
            logger.info("[email] skipped match %s: mentor has no email address", match_id)
            return False
        build_mentor_email(job).send(fail_silently=False)
        logger.info("[email] new_question q%s -> %s (match %s)", job.question_id, job.to, match_id)
        return True
    except Exception:
        logger.exception("[email] new_question email for match %s failed", match_id)
        return False


def send_mentor_emails(jobs):
    """Send every MentorEmail in `jobs`, one by one; one failure doesn't stop the rest. Never raises.

    This is the background thread's target, so it closes the thread's DB connection at the end.
    """
    try:
        for job in jobs:
            email_mentor(job)
    finally:
        try:
            connection.close()
        except Exception:
            logger.exception("[email] closing the DB connection failed")


def start_mentor_emails(jobs):
    """Send `jobs` (MentorEmail values) without blocking the caller.

    Starts a daemon thread and returns it. With settings.NOTIFY_EMAILS_SYNC = True (tests) it sends inline
    and returns None. Returns None when there's nothing to send.
    """
    jobs = list(jobs)
    if not jobs:
        return None
    if getattr(settings, "NOTIFY_EMAILS_SYNC", False):
        for job in jobs:
            email_mentor(job)
        return None
    thread = threading.Thread(target=send_mentor_emails, args=(jobs,), name="mentor-emails", daemon=True)
    thread.start()
    return thread


# ============================================================================
# NOTIFY HOOK: new question -> each matched mentor
# ============================================================================
def notify_matched_mentors(question, matches):
    """Tell each matched mentor about a new question: a WebSocket push, then an email.

    `question` is the saved Question (question.mentee is loaded). `matches` is the list of saved
    QuestionMatch objects in rank order; each has .id, .mentor_id, .reason and .rank.
    Pushes happen inline (they're fast); emails go out on a background thread.
    """
    for match in matches:
        try:
            # --- Phase 5: live WebSocket event -------------------------------------------------------
            sent = push(match.mentor_id, new_question_event(question, match))
            logger.info(
                "[notify] new_question q%s -> mentor %s (match %s, rank %s)%s",
                question.id, match.mentor_id, match.id, match.rank, "" if sent else " [push FAILED]",
            )
        except Exception:  # one bad match must not stop the rest
            logger.exception("notify_matched_mentors failed for match %s", getattr(match, "id", None))

    # --- Phase 6: email, off the request thread --------------------------------------------------------
    # Gather plain values here (one query for all mentors) so the thread never touches a model or the DB.
    try:
        mentors = User.objects.select_related("profile").in_bulk([m.mentor_id for m in matches])
        jobs = [
            mentor_email_for(question, match, mentors[match.mentor_id])
            for match in matches
            if match.mentor_id in mentors
        ]
        start_mentor_emails(jobs)
    except Exception:
        logger.exception("Starting mentor emails for question %s failed", getattr(question, "id", None))


# ============================================================================
# NOTIFY HOOK: new answer -> the question's mentee
# ============================================================================
def notify_mentee_of_answer(answer):
    """Tell the mentee that a mentor answered their question.

    `answer` is the saved Answer. answer.match is loaded with .question (and .question.mentee) and
    .mentor (and .mentor.profile), so building the event needs no extra queries.
    """
    match = answer.match
    mentee_id = match.question.mentee_id

    # --- Phase 5: live WebSocket event -------------------------------------------------------------
    sent = push(mentee_id, new_answer_event(answer))
    logger.info(
        "[notify] new_answer a%s (match %s, q%s) -> mentee %s from mentor %s%s",
        answer.id, match.id, match.question_id, mentee_id, match.mentor_id, "" if sent else " [push FAILED]",
    )

    # No email here: Phase 6 only emails matched mentors. The mentee gets the answer live (above) and
    # in GET /questions/mine/.
