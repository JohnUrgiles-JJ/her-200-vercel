"""Notifications for matched mentors.

Called from QuestionCreateView via transaction.on_commit, after the Question and its QuestionMatch rows
are saved, inside a try/except, so nothing here can fail the request.
"""

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# NOTIFY HOOK: Phases 5 and 6 fill this in.
# ============================================================================
def notify_matched_mentors(question, matches):
    """Tell each matched mentor about a new question.

    `question` is the saved Question (question.mentee is loaded). `matches` is the list of saved
    QuestionMatch objects in rank order; each has .id, .mentor (User), .reason and .rank.

    TODO Phase 5: send {"event": "new_question", ...} over Channels to group f"user_{match.mentor_id}"
                  (shape in Section 3.3 of the plan).
    TODO Phase 6: email each mentor at match.mentor.email; email failures must never raise.
    """
    for match in matches:
        print(
            f"[notify] question {question.id} -> mentor {match.mentor_id} "
            f"(match {match.id}, rank {match.rank}): {match.reason}"
        )
