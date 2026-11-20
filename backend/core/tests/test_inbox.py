from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import Answer, Question, QuestionMatch
from core.serializers import short_name
from core.tests.test_questions import FAST_HASHER, client_for, make_user

INBOX_KEYS = {"match_id", "question_id", "question_text", "mentee_name", "reason", "status", "created_at", "answers"}
ANSWER_KEYS = {"id", "text", "created_at"}


def ask(mentee, text, mentors, minutes_ago=0):
    """Create a question with one match per mentor (rank order), `minutes_ago` in the past."""
    question = Question.objects.create(mentee=mentee, text=text)
    if minutes_ago:
        Question.objects.filter(pk=question.pk).update(created_at=timezone.now() - timedelta(minutes=minutes_ago))
    matches = [
        QuestionMatch.objects.create(question=question, mentor=m, reason=f"Reason for {m.email}", rank=rank)
        for rank, m in enumerate(mentors, start=1)
    ]
    return question, matches


class ShortNameTests(SimpleTestCase):
    def _user(self, full_name):
        return SimpleNamespace(profile=SimpleNamespace(full_name=full_name))

    def test_formats(self):
        cases = {
            "Maria Lopez": "Maria L.",
            "Cher": "Cher",
            "  Aisha   Rahman ": "Aisha R.",
            "Ana Maria de la Cruz": "Ana C.",
            "": "",
        }
        for full_name, expected in cases.items():
            with self.subTest(full_name=full_name):
                self.assertEqual(short_name(self._user(full_name)), expected)


@FAST_HASHER
class InboxTests(APITestCase):
    def setUp(self):
        self.maya, maya_token = make_user("maya@t.com", "Maya Chen", "mentor")
        self.priya, priya_token = make_user("priya@t.com", "Priya Nair", "mentor")
        self.maria, self.maria_token = make_user("maria@t.com", "Maria Lopez", "mentee")
        self.cher, _ = make_user("cher@t.com", "Cher", "mentee")
        self.maya_client = client_for(maya_token)
        self.priya_client = client_for(priya_token)

        # Oldest first: q_old (Maya + Priya), q_mid (Priya only), q_new (Maya + Priya, from Cher).
        self.q_old, self.old_matches = ask(self.maria, "How do I build a UX portfolio?", [self.maya, self.priya], 30)
        self.q_mid, self.mid_matches = ask(self.maria, "Data science internships?", [self.priya], 20)
        self.q_new, self.new_matches = ask(self.cher, "Can I switch into UX at 40?", [self.priya, self.maya], 10)

    def test_mentor_sees_only_own_matches_newest_first(self):
        res = self.maya_client.get("/api/inbox/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([i["question_id"] for i in res.data], [self.q_new.id, self.q_old.id])
        self.assertEqual([i["match_id"] for i in res.data], [self.new_matches[1].id, self.old_matches[0].id])

        priya = self.priya_client.get("/api/inbox/").data
        self.assertEqual([i["question_id"] for i in priya], [self.q_new.id, self.q_mid.id, self.q_old.id])

    def test_item_shape_and_values(self):
        Answer.objects.create(match=self.old_matches[0], text="First answer")
        Answer.objects.create(match=self.old_matches[0], text="Second answer")
        Answer.objects.create(match=self.old_matches[1], text="Priya's answer, not Maya's")

        items = self.maya_client.get("/api/inbox/").data
        for item in items:
            self.assertEqual(set(item), INBOX_KEYS)

        new, old = items
        self.assertEqual(new["mentee_name"], "Cher")
        self.assertEqual(old["mentee_name"], "Maria L.")
        self.assertEqual(old["question_text"], "How do I build a UX portfolio?")
        self.assertEqual(old["reason"], "Reason for maya@t.com")
        self.assertEqual(old["status"], "sent")
        self.q_old.refresh_from_db()
        self.assertEqual(old["created_at"], self.q_old.created_at.isoformat().replace("+00:00", "Z"))
        self.assertEqual([a["text"] for a in old["answers"]], ["First answer", "Second answer"])
        self.assertEqual(set(old["answers"][0]), ANSWER_KEYS)
        self.assertEqual(new["answers"], [])

    def test_no_private_mentee_fields(self):
        body = self.maya_client.get("/api/inbox/").content.decode()
        self.assertNotIn("maria@t.com", body)
        self.assertNotIn("Lopez", body)

    def test_status_filter(self):
        QuestionMatch.objects.filter(pk=self.old_matches[1].pk).update(status="answered")

        answered = self.priya_client.get("/api/inbox/?status=answered").data
        self.assertEqual([i["match_id"] for i in answered], [self.old_matches[1].id])
        sent = self.priya_client.get("/api/inbox/?status=sent").data
        self.assertEqual([i["match_id"] for i in sent], [self.new_matches[0].id, self.mid_matches[0].id])
        self.assertEqual(len(self.priya_client.get("/api/inbox/?status=").data), 3)  # blank = no filter

        bad = self.priya_client.get("/api/inbox/?status=pending")
        self.assertEqual(bad.status_code, 400)
        self.assertIn("detail", bad.data)

    def test_query_count_is_constant(self):
        for i in range(5):
            _, matches = ask(self.maria, f"Extra question {i}", [self.maya])
            Answer.objects.create(match=matches[0], text=f"Answer {i}")
        # auth (token+user), profile for IsMentor, matches+question+mentee+profile, answers
        with self.assertNumQueries(4):
            res = self.maya_client.get("/api/inbox/")
        self.assertEqual(len(res.data), 7)

    def test_mentee_forbidden_and_anonymous_unauthorized(self):
        self.assertEqual(client_for(self.maria_token).get("/api/inbox/").status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get("/api/inbox/").status_code, 401)


@FAST_HASHER
class AnswerTests(APITestCase):
    def setUp(self):
        self.maya, maya_token = make_user("maya@t.com", "Maya Chen", "mentor")
        self.priya, _ = make_user("priya@t.com", "Priya Nair", "mentor")
        self.maria, self.maria_token = make_user("maria@t.com", "Maria Lopez", "mentee")
        self.maya_client = client_for(maya_token)
        self.question, (self.maya_match, self.priya_match) = ask(
            self.maria, "How do I break into UX design without a degree?", [self.maya, self.priya]
        )

    def url(self, match_id):
        return f"/api/matches/{match_id}/answer/"

    def test_answer_own_match_then_mentee_sees_it(self):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.maya_client.post(self.url(self.maya_match.id), {"text": "  Start with 3 case studies.  "}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(set(res.data), ANSWER_KEYS)
        self.assertEqual(res.data["text"], "Start with 3 case studies.")

        self.maya_match.refresh_from_db()
        self.assertEqual(self.maya_match.status, "answered")
        self.priya_match.refresh_from_db()
        self.assertEqual(self.priya_match.status, "sent")

        mine = client_for(self.maria_token).get("/api/questions/mine/").data
        matches = {m["match_id"]: m for m in mine[0]["matches"]}
        self.assertEqual(matches[self.maya_match.id]["status"], "answered")
        self.assertEqual(matches[self.maya_match.id]["answers"], [res.data])
        self.assertEqual(matches[self.priya_match.id]["answers"], [])

        inbox = self.maya_client.get("/api/inbox/").data
        self.assertEqual(inbox[0]["status"], "answered")
        self.assertEqual(inbox[0]["answers"], [res.data])

    def test_multiple_answers_allowed(self):
        self.maya_client.post(self.url(self.maya_match.id), {"text": "One"}, format="json")
        res = self.maya_client.post(self.url(self.maya_match.id), {"text": "Two"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.maya_match.refresh_from_db()
        self.assertEqual(self.maya_match.status, "answered")
        self.assertEqual(list(self.maya_match.answers.values_list("text", flat=True)), ["One", "Two"])

    def test_other_mentors_match_is_404(self):
        res = self.maya_client.post(self.url(self.priya_match.id), {"text": "Sneaky"}, format="json")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data, {"detail": "Not found."})
        # Same 404 even with a bad body, so the response never hints that the match exists.
        self.assertEqual(self.maya_client.post(self.url(self.priya_match.id), {}, format="json").status_code, 404)
        self.assertFalse(Answer.objects.exists())
        self.priya_match.refresh_from_db()
        self.assertEqual(self.priya_match.status, "sent")

    def test_missing_match_is_404(self):
        res = self.maya_client.post(self.url(999999), {"text": "Hello"}, format="json")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data, {"detail": "Not found."})

    def test_mentee_forbidden_and_anonymous_unauthorized(self):
        res = client_for(self.maria_token).post(self.url(self.maya_match.id), {"text": "Hi"}, format="json")
        self.assertEqual(res.status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.post(self.url(self.maya_match.id), {"text": "Hi"}, format="json").status_code, 401)
        self.assertFalse(Answer.objects.exists())

    def test_bad_text_is_400(self):
        for body in [{"text": ""}, {"text": "   \n "}, {}, {"text": None}, {"text": 123}, {"text": ["a"]}]:
            with self.subTest(body=body):
                res = self.maya_client.post(self.url(self.maya_match.id), body, format="json")
                self.assertEqual(res.status_code, 400)
                self.assertEqual(res.data, {"detail": "Answer text is required."})
        self.assertFalse(Answer.objects.exists())
        self.maya_match.refresh_from_db()
        self.assertEqual(self.maya_match.status, "sent")

    def test_length_limit(self):
        too_long = self.maya_client.post(self.url(self.maya_match.id), {"text": "a" * 3001}, format="json")
        self.assertEqual(too_long.status_code, 400)
        self.assertEqual(too_long.data, {"detail": "Answer must be at most 3000 characters."})
        ok = self.maya_client.post(self.url(self.maya_match.id), {"text": "a" * 3000 + "   "}, format="json")
        self.assertEqual(ok.status_code, 201)

    def test_notify_runs_after_commit(self):
        with mock.patch("core.notify.notify_mentee_of_answer") as notify:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                res = self.maya_client.post(self.url(self.maya_match.id), {"text": "Hello"}, format="json")
            notify.assert_not_called()
            self.assertEqual(len(callbacks), 1)
            callbacks[0]()
        answer = notify.call_args.args[0]
        self.assertEqual(answer.id, res.data["id"])
        self.assertEqual(answer.match.question.mentee_id, self.maria.id)

    def test_notify_failure_does_not_fail_request(self):
        with mock.patch("core.notify.notify_mentee_of_answer", side_effect=RuntimeError("boom")):
            with self.assertLogs("core.views", level="ERROR"):
                with self.captureOnCommitCallbacks(execute=True):
                    res = self.maya_client.post(self.url(self.maya_match.id), {"text": "Hello"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Answer.objects.count(), 1)

    def test_real_notify_pushes_new_answer(self):
        with mock.patch("core.notify.push", return_value=True) as push, self.captureOnCommitCallbacks(execute=True):
            res = self.maya_client.post(self.url(self.maya_match.id), {"text": "Hello"}, format="json")
        push.assert_called_once_with(
            self.maria.id,
            {
                "event": "new_answer",
                "question_id": self.maya_match.question_id,
                "match_id": self.maya_match.id,
                "mentor_name": "Maya Chen",
                "text": "Hello",
            },
        )
        self.assertEqual(res.status_code, 201)
