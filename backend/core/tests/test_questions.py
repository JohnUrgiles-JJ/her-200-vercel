import os
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from core import matching
from core.models import Answer, MentorProfile, Profile, Question, QuestionMatch

MATCH_KEYS = {"match_id", "mentor_id", "name", "headline", "company", "reason", "rank", "status", "answers"}
QUESTION_KEYS = {"id", "text", "created_at", "matches"}
UX_QUESTION = "How do I break into UX design without a design degree?"

MENTOR_DATA = [
    # (email, name, headline, company, fields, open_to, years, bio)
    (
        "maya@t.com", "Maya Chen", "UX Designer", "Figma",
        "UX, product design, Figma, user research", "career switching, portfolios", 6,
        "Taught art before switching into UX with no design degree.",
    ),
    (
        "priya@t.com", "Priya Nair", "Data Scientist", "Spotify",
        "data science, Python, machine learning", "grad school, internships", 5,
        "Master's in statistics, first internship from a research lab.",
    ),
    (
        "amara@t.com", "Amara Okafor", "Cybersecurity Analyst", "JPMorgan Chase",
        "cybersecurity, networking, security certifications", "certifications, help desk to security", 7,
        "Started on the help desk and earned Security+ at night.",
    ),
    (
        "sofia@t.com", "Sofia Martinez", "Software Engineer", "Microsoft",
        "backend, Python, APIs", "first job, technical interviews, imposter syndrome", 4,
        "First-gen CS grad who failed six interviews before landing one.",
    ),
]

NO_LLM = {"LLM_PROVIDER": "none"}
# Tests create many users; the default PBKDF2 hasher made this file take ~80 s.
FAST_HASHER = override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])


def make_user(email, name, role):
    user = User.objects.create_user(username=email, email=email, password="secret123")
    Profile.objects.create(user=user, role=role, full_name=name)
    return user, Token.objects.create(user=user).key


def make_mentors():
    mentors = {}
    for email, name, headline, company, fields, open_to, years, bio in MENTOR_DATA:
        user, _ = make_user(email, name, "mentor")
        MentorProfile.objects.create(
            user=user, headline=headline, company=company, fields=fields,
            open_to=open_to, bio=bio, experience_years=years,
        )
        mentors[name.split()[0].lower()] = user
    return mentors


def client_for(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@mock.patch.dict(os.environ, NO_LLM)
@FAST_HASHER
class AskQuestionTests(APITestCase):
    def setUp(self):
        self.mentors = make_mentors()
        self.mentee, token = make_user("maria@t.com", "Maria Lopez", "mentee")
        self.client = client_for(token)

    def test_ask_returns_201_with_three_full_matches(self):
        fake = [
            {"mentor_id": self.mentors["maya"].id, "reason": "Switched into UX from teaching"},
            {"mentor_id": self.mentors["sofia"].id, "reason": "First-gen and broke in anyway"},
            {"mentor_id": self.mentors["priya"].id, "reason": "Built a portfolio from research"},
        ]
        with mock.patch("core.views.matching.match_mentors", return_value=fake) as m:
            res = self.client.post("/api/questions/", {"text": f"  {UX_QUESTION}  "}, format="json")
        m.assert_called_once_with(UX_QUESTION, k=3)

        self.assertEqual(res.status_code, 201)
        self.assertEqual(set(res.data), QUESTION_KEYS)
        self.assertEqual(res.data["text"], UX_QUESTION)
        self.assertEqual(len(res.data["matches"]), 3)
        for match in res.data["matches"]:
            self.assertEqual(set(match), MATCH_KEYS)
            self.assertEqual(match["status"], "sent")
            self.assertEqual(match["answers"], [])
        first = res.data["matches"][0]
        self.assertEqual(
            {k: first[k] for k in ("mentor_id", "name", "headline", "company", "reason", "rank")},
            {
                "mentor_id": self.mentors["maya"].id, "name": "Maya Chen", "headline": "UX Designer",
                "company": "Figma", "reason": "Switched into UX from teaching", "rank": 1,
            },
        )
        self.assertEqual([m["rank"] for m in res.data["matches"]], [1, 2, 3])
        self.assertEqual(first["match_id"], QuestionMatch.objects.get(rank=1).id)
        self.assertEqual(Question.objects.get().mentee, self.mentee)

    def test_ask_end_to_end_with_keyword_fallback(self):
        res = self.client.post("/api/questions/", {"text": UX_QUESTION}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.data["matches"]), 3)
        self.assertEqual(res.data["matches"][0]["name"], "Maya Chen")
        self.assertEqual(QuestionMatch.objects.count(), 3)

    def test_text_too_short(self):
        res = self.client.post("/api/questions/", {"text": "   help?   "}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("detail", res.data)
        self.assertEqual(Question.objects.count(), 0)

    def test_text_too_long_or_missing(self):
        self.assertEqual(self.client.post("/api/questions/", {"text": "x" * 1001}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/questions/", {}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/questions/", {"text": 12345678901}, format="json").status_code, 400)
        self.assertEqual(Question.objects.count(), 0)

    def test_mentor_cannot_ask(self):
        mentor_token = Token.objects.get(user=self.mentors["maya"]).key
        res = client_for(mentor_token).post("/api/questions/", {"text": UX_QUESTION}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data, {"detail": "Only mentees can ask questions."})

    def test_unauthenticated(self):
        res = APIClient().post("/api/questions/", {"text": UX_QUESTION}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_no_mentors_still_creates_question(self):
        MentorProfile.objects.all().delete()
        res = self.client.post("/api/questions/", {"text": UX_QUESTION}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["matches"], [])
        self.assertEqual(Question.objects.count(), 1)

    def test_fewer_mentors_than_k(self):
        MentorProfile.objects.exclude(user=self.mentors["maya"]).delete()
        res = self.client.post("/api/questions/", {"text": UX_QUESTION}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual([m["name"] for m in res.data["matches"]], ["Maya Chen"])

    def test_notify_runs_after_commit(self):
        with mock.patch("core.views.notify.notify_matched_mentors") as notify_mock:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                res = self.client.post("/api/questions/", {"text": UX_QUESTION}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(callbacks), 1)
        question, matches = notify_mock.call_args.args
        self.assertEqual(question.id, res.data["id"])
        self.assertEqual([m.id for m in matches], [m["match_id"] for m in res.data["matches"]])

    def test_notify_failure_does_not_fail_request(self):
        with mock.patch("core.views.notify.notify_matched_mentors", side_effect=RuntimeError("boom")):
            with self.assertLogs("core.views", level="ERROR"):
                with self.captureOnCommitCallbacks(execute=True):
                    res = self.client.post("/api/questions/", {"text": UX_QUESTION}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Question.objects.count(), 1)

    def test_matching_crash_still_creates_question(self):
        with mock.patch("core.views.matching.match_mentors", side_effect=RuntimeError("boom")):
            with self.assertLogs("core.views", level="ERROR"):
                res = self.client.post("/api/questions/", {"text": UX_QUESTION}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["matches"], [])


@mock.patch.dict(os.environ, NO_LLM)
@FAST_HASHER
class MyQuestionsTests(APITestCase):
    def setUp(self):
        self.mentors = make_mentors()
        self.maria, maria_token = make_user("maria@t.com", "Maria Lopez", "mentee")
        self.aisha, aisha_token = make_user("aisha@t.com", "Aisha Rahman", "mentee")
        self.maria_client = client_for(maria_token)
        self.aisha_client = client_for(aisha_token)

    def test_only_own_questions_newest_first_with_answers(self):
        self.maria_client.post("/api/questions/", {"text": UX_QUESTION}, format="json")
        second = self.maria_client.post(
            "/api/questions/", {"text": "Which cybersecurity certifications should I get first?"}, format="json"
        ).data
        self.aisha_client.post("/api/questions/", {"text": "How do I get a data science internship?"}, format="json")

        match = QuestionMatch.objects.get(id=second["matches"][0]["match_id"])
        Answer.objects.create(match=match, text="Start with Security+.")
        match.status = "answered"
        match.save()

        res = self.maria_client.get("/api/questions/mine/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)
        self.assertEqual([q["id"] for q in res.data], [second["id"], second["id"] - 1])
        self.assertTrue(all(set(q) == QUESTION_KEYS for q in res.data))
        top = res.data[0]["matches"][0]
        self.assertEqual(top["status"], "answered")
        self.assertEqual(len(top["answers"]), 1)
        self.assertEqual(set(top["answers"][0]), {"id", "text", "created_at"})
        self.assertEqual(top["answers"][0]["text"], "Start with Security+.")

        aisha_res = self.aisha_client.get("/api/questions/mine/")
        self.assertEqual(len(aisha_res.data), 1)
        self.assertEqual(aisha_res.data[0]["text"], "How do I get a data science internship?")

    def test_list_query_count_is_constant(self):
        for i in range(5):
            self.maria_client.post("/api/questions/", {"text": f"{UX_QUESTION} ({i})"}, format="json")
        # auth (token+user), profile for IsMentee, questions, matches+mentor joins, answers
        with self.assertNumQueries(5):
            res = self.maria_client.get("/api/questions/mine/")
        self.assertEqual(len(res.data), 5)

    def test_mentor_forbidden(self):
        token = Token.objects.get(user=self.mentors["maya"]).key
        self.assertEqual(client_for(token).get("/api/questions/mine/").status_code, 403)


@FAST_HASHER
class KeywordFallbackTests(TestCase):
    def setUp(self):
        self.mentors = make_mentors()
        self.profiles = list(MentorProfile.objects.select_related("user").order_by("user_id"))

    def test_picks_ux_mentor_for_ux_question(self):
        results = matching.keyword_fallback(UX_QUESTION, self.profiles, 3)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["mentor_id"], self.mentors["maya"].id)
        self.assertEqual(results[0]["reason"], "Experience in UX")

    def test_picks_security_mentor_for_cert_question(self):
        results = matching.keyword_fallback("Which cybersecurity certification should I get?", self.profiles, 3)
        self.assertEqual(results[0]["mentor_id"], self.mentors["amara"].id)
        self.assertEqual(results[0]["reason"], "Experience in cybersecurity")

    def test_reason_uses_open_to_topic_when_no_field_matches(self):
        results = matching.keyword_fallback("How do I deal with imposter syndrome at work?", self.profiles, 1)
        self.assertEqual(results, [{"mentor_id": self.mentors["sofia"].id, "reason": "Experience in imposter syndrome"}])

    def test_no_overlap_uses_experience_and_first_field(self):
        results = matching.keyword_fallback("Hello there friends, zzz qqq?", self.profiles, 2)
        self.assertEqual(results[0]["mentor_id"], self.mentors["amara"].id)  # 7 years, most experience
        self.assertEqual(results[0]["reason"], "Experience in cybersecurity")
        self.assertEqual(results[1]["mentor_id"], self.mentors["maya"].id)  # 6 years

    def test_k_larger_than_mentors(self):
        self.assertEqual(len(matching.keyword_fallback(UX_QUESTION, self.profiles, 10)), 4)


def fake_anthropic_response(text, stop_reason="end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


@mock.patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test-key"})
@FAST_HASHER
class LLMMatchingTests(TestCase):
    """The provider SDK is mocked, so no real API is ever called."""

    def setUp(self):
        self.mentors = make_mentors()

    def _patch_create(self, **kwargs):
        patcher = mock.patch("anthropic.resources.messages.Messages.create", autospec=True, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_valid_response_is_used(self):
        ids = self.mentors
        self._patch_create(return_value=fake_anthropic_response(
            'Here you go:\n```json\n['
            f'{{"mentor_id": {ids["maya"].id}, "reason": "Switched into UX from teaching, like you"}},'
            f'{{"mentor_id": "{ids["sofia"].id}", "reason": "First-gen and self-taught"}},'
            f'{{"mentor_id": {ids["priya"].id}, "reason": "Turned research into a portfolio"}}'
            ']\n```'
        ))
        results = matching.match_mentors(UX_QUESTION)
        self.assertEqual(
            results,
            [
                {"mentor_id": ids["maya"].id, "reason": "Switched into UX from teaching, like you"},
                {"mentor_id": ids["sofia"].id, "reason": "First-gen and self-taught"},
                {"mentor_id": ids["priya"].id, "reason": "Turned research into a portfolio"},
            ],
        )

    def test_request_parameters(self):
        create = self._patch_create(return_value=fake_anthropic_response("[]"))
        matching.match_mentors(UX_QUESTION)
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-haiku-5-5")
        self.assertEqual(kwargs["max_tokens"], 500)
        prompt = kwargs["messages"][0]["content"]
        self.assertIn(UX_QUESTION, prompt)
        self.assertIn(f'{self.mentors["maya"].id} | Maya Chen | UX Designer | Figma |', prompt)
        self.assertIn("exactly 3 objects", prompt)
        client = create.call_args.args[0]._client
        self.assertEqual(client.timeout, matching.LLM_TIMEOUT_SECONDS)

    def test_junk_response_falls_back_to_keywords(self):
        self._patch_create(return_value=fake_anthropic_response("Sorry, I can't help with that!"))
        with self.assertLogs("core.matching", level="WARNING"):
            results = matching.match_mentors(UX_QUESTION)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], {"mentor_id": self.mentors["maya"].id, "reason": "Experience in UX"})

    def test_broken_json_falls_back(self):
        self._patch_create(return_value=fake_anthropic_response('[{"mentor_id": 1, "reason": "x",]'))
        with self.assertLogs("core.matching", level="WARNING"):
            results = matching.match_mentors(UX_QUESTION)
        self.assertEqual(results[0]["mentor_id"], self.mentors["maya"].id)

    def test_api_error_falls_back(self):
        self._patch_create(side_effect=ConnectionError("network down"))
        with self.assertLogs("core.matching", level="WARNING"):
            results = matching.match_mentors(UX_QUESTION)
        self.assertEqual(len(results), 3)

    def test_invalid_and_duplicate_ids_are_topped_up(self):
        maya = self.mentors["maya"].id
        self._patch_create(return_value=fake_anthropic_response(
            f'[{{"mentor_id": {maya}, "reason": "{"word " * 80}"}},'
            f'{{"mentor_id": {maya}, "reason": "dup"}},'
            '{"mentor_id": 99999, "reason": "not a mentor"}, "junk", {"reason": "no id"}]'
        ))
        with self.assertLogs("core.matching", level="WARNING"):
            results = matching.match_mentors(UX_QUESTION)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["mentor_id"], maya)
        self.assertLessEqual(len(results[0]["reason"]), 200)
        self.assertEqual(len({r["mentor_id"] for r in results}), 3)

    def test_missing_key_skips_api(self):
        create = self._patch_create()
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            results = matching.match_mentors(UX_QUESTION)
        create.assert_not_called()
        self.assertEqual(results[0]["mentor_id"], self.mentors["maya"].id)

    def test_openai_junk_falls_back(self):
        fake = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="nope"))])
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}), \
                mock.patch("openai.resources.chat.completions.Completions.create", return_value=fake) as create:
            with self.assertLogs("core.matching", level="WARNING"):
                results = matching.match_mentors(UX_QUESTION)
        self.assertEqual(create.call_args.kwargs["model"], "gpt-4o-mini")
        self.assertEqual(results[0]["mentor_id"], self.mentors["maya"].id)

    def test_no_mentors_returns_empty(self):
        create = self._patch_create()
        MentorProfile.objects.all().delete()
        self.assertEqual(matching.match_mentors(UX_QUESTION), [])
        create.assert_not_called()
