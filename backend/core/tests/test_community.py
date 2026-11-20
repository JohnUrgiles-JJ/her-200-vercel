import os
from unittest import mock

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core.models import Answer, Question, QuestionMatch

from .test_questions import FAST_HASHER, NO_LLM, UX_QUESTION, client_for, make_mentors, make_user

COMMUNITY_KEYS = {"id", "text", "mentee_name", "created_at", "matches"}
COMMUNITY_MATCH_KEYS = {"match_id", "mentor_id", "name", "headline", "company", "answers"}
DATA_QUESTION = "How do I get a data science internship?"


@mock.patch.dict(os.environ, NO_LLM)
@FAST_HASHER
class CommunityFeedTests(APITestCase):
    def setUp(self):
        self.mentors = make_mentors()
        self.maria, maria_token = make_user("maria@t.com", "Maria Lopez", "mentee")
        self.aisha, aisha_token = make_user("aisha@t.com", "Aisha Rahman", "mentee")
        self.maria_client = client_for(maria_token)
        self.aisha_client = client_for(aisha_token)

    def ask(self, client, text, **extra):
        return client.post("/api/questions/", {"text": text, **extra}, format="json")

    def answer(self, match_id, text):
        match = QuestionMatch.objects.get(pk=match_id)
        Answer.objects.create(match=match, text=text)
        QuestionMatch.objects.filter(pk=match_id).update(status="answered")

    def test_questions_are_private_by_default(self):
        res = self.ask(self.maria_client, UX_QUESTION)
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data["is_public"])
        self.assertEqual(self.aisha_client.get("/api/questions/community/").data, [])

    def test_public_question_shows_to_others_with_answers_only(self):
        q = self.ask(self.maria_client, UX_QUESTION, is_public=True).data
        self.assertTrue(q["is_public"])
        self.assertGreaterEqual(len(q["matches"]), 2)
        answered, unanswered = q["matches"][0], q["matches"][1]
        self.answer(answered["match_id"], "Build a portfolio from three redesigns.")

        res = self.aisha_client.get("/api/questions/community/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        item = res.data[0]
        self.assertEqual(set(item), COMMUNITY_KEYS)
        self.assertEqual(item["text"], UX_QUESTION)
        self.assertEqual(item["mentee_name"], "Maria L.")  # short name, never the email
        self.assertEqual([m["match_id"] for m in item["matches"]], [answered["match_id"]])
        self.assertNotIn(unanswered["match_id"], [m["match_id"] for m in item["matches"]])
        self.assertEqual(set(item["matches"][0]), COMMUNITY_MATCH_KEYS)  # no private matching reason
        self.assertEqual(item["matches"][0]["answers"][0]["text"], "Build a portfolio from three redesigns.")

    def test_own_questions_left_out(self):
        self.ask(self.maria_client, UX_QUESTION, is_public=True)
        self.assertEqual(self.maria_client.get("/api/questions/community/").data, [])

    def test_newest_first(self):
        first = self.ask(self.maria_client, UX_QUESTION, is_public=True).data
        second = self.ask(self.maria_client, DATA_QUESTION, is_public=True).data
        ids = [q["id"] for q in self.aisha_client.get("/api/questions/community/").data]
        self.assertEqual(ids, [second["id"], first["id"]])

    def test_mentors_can_read_the_feed(self):
        self.ask(self.maria_client, UX_QUESTION, is_public=True)
        token = Token.objects.get(user=self.mentors["maya"]).key
        res = client_for(token).get("/api/questions/community/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_unauthenticated(self):
        self.assertEqual(self.client.get("/api/questions/community/").status_code, 401)

    def test_is_public_must_be_bool_on_create(self):
        res = self.ask(self.maria_client, UX_QUESTION, is_public="yes")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Question.objects.count(), 0)

    def test_query_count_is_constant(self):
        for i in range(5):
            q = self.ask(self.maria_client, f"{UX_QUESTION} ({i})", is_public=True).data
            self.answer(q["matches"][0]["match_id"], "An answer.")
        # auth (token+user), questions+mentee profile, matches+mentor joins, answers
        with self.assertNumQueries(4):
            res = self.aisha_client.get("/api/questions/community/")
        self.assertEqual(len(res.data), 5)

    # --- PATCH /questions/<id>/ ---------------------------------------------

    def test_owner_can_share_and_unshare(self):
        q = self.ask(self.maria_client, UX_QUESTION).data
        res = self.maria_client.patch(f"/api/questions/{q['id']}/", {"is_public": True}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_public"])
        self.assertEqual(len(self.aisha_client.get("/api/questions/community/").data), 1)

        res = self.maria_client.patch(f"/api/questions/{q['id']}/", {"is_public": False}, format="json")
        self.assertFalse(res.data["is_public"])
        self.assertEqual(self.aisha_client.get("/api/questions/community/").data, [])

    def test_cannot_share_someone_elses_question(self):
        q = self.ask(self.maria_client, UX_QUESTION).data
        res = self.aisha_client.patch(f"/api/questions/{q['id']}/", {"is_public": True}, format="json")
        self.assertEqual(res.status_code, 404)
        self.assertFalse(Question.objects.get(pk=q["id"]).is_public)

    def test_patch_requires_bool(self):
        q = self.ask(self.maria_client, UX_QUESTION).data
        res = self.maria_client.patch(f"/api/questions/{q['id']}/", {"is_public": "true"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.maria_client.patch(f"/api/questions/{q['id']}/", {}, format="json").status_code, 400)

    def test_mentor_cannot_patch(self):
        q = self.ask(self.maria_client, UX_QUESTION).data
        token = Token.objects.get(user=self.mentors["maya"]).key
        res = client_for(token).patch(f"/api/questions/{q['id']}/", {"is_public": True}, format="json")
        self.assertEqual(res.status_code, 403)
