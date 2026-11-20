"""Notifications: new questions for matched mentors, new answers for mentees.

Both hooks run via transaction.on_commit (from QuestionCreateView and AnswerCreateView), after the rows
are saved, inside a try/except, so nothing here can fail the request. push() also never raises on its own.

Live delivery (Phase 5) goes over Django Channels to the group f"user_{id}" that each connected socket joins
(core/consumers.py). Event shapes are fixed by Section 3.3 of the plan.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

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
# NOTIFY HOOK: new question -> each matched mentor
# ============================================================================
def notify_matched_mentors(question, matches):
    """Tell each matched mentor about a new question.

    `question` is the saved Question (question.mentee is loaded). `matches` is the list of saved
    QuestionMatch objects in rank order; each has .id, .mentor_id, .reason and .rank.
    """
    for match in matches:
        try:
            # --- Phase 5: live WebSocket event -------------------------------------------------------
            sent = push(match.mentor_id, new_question_event(question, match))
            logger.info(
                "[notify] new_question q%s -> mentor %s (match %s, rank %s)%s",
                question.id, match.mentor_id, match.id, match.rank, "" if sent else " [push FAILED]",
            )

            # --- Phase 6: EMAIL GOES HERE ------------------------------------------------------------
            # Email the mentor at match.mentor.email. Must never raise (wrap in its own try/except), and
            # a failure for one mentor must not stop the others.
        except Exception:  # one bad match must not stop the rest
            logger.exception("notify_matched_mentors failed for match %s", getattr(match, "id", None))


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

    # --- Phase 6: EMAIL GOES HERE ------------------------------------------------------------------
    # Email the mentee at match.question.mentee.email. Must never raise (wrap in its own try/except).
