"""Phase 7 hardening: JSON errors under /api/, CORS for the Vite dev origin, the startup LLM notice."""

import os
from unittest import mock

from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import include, path
from rest_framework.test import APIClient

from core import matching, views
from core.exceptions import SERVER_ERROR
from core.tests.test_questions import FAST_HASHER, client_for, make_user

FRONTEND = "http://localhost:5173"


def plain_django_view_that_crashes(request):
    raise RuntimeError("boom outside DRF")


def plain_django_view_html_400(request):
    return HttpResponse("<h1>Bad</h1>", status=400)


# Used as ROOT_URLCONF by PlainViewErrorTests: two non-DRF views under /api/, then the real URLs.
urlpatterns = [
    path("api/test-crash/", plain_django_view_that_crashes),
    path("api/test-html-400/", plain_django_view_html_400),
    path("", include("connecther.urls")),
]


@FAST_HASHER
class JsonErrorTests(TestCase):
    def setUp(self):
        self.mentor, token = make_user("maya@t.com", "Maya Chen", "mentor")
        self.client = client_for(token)

    def assert_json_error(self, res, code, detail):
        self.assertEqual(res.status_code, code)
        self.assertTrue(res["Content-Type"].startswith("application/json"), res["Content-Type"])
        self.assertEqual(res.json(), {"detail": detail})

    def test_crash_in_drf_view_is_json_500(self):
        with mock.patch.object(views.InboxView, "get", side_effect=RuntimeError("db exploded")):
            with self.assertLogs("core.exceptions", level="ERROR") as logs:
                res = self.client.get("/api/inbox/")
        self.assert_json_error(res, 500, SERVER_ERROR)
        self.assertIn("GET /api/inbox/", logs.output[0])
        self.assertIn("db exploded", "\n".join(logs.output))  # the traceback is logged

    @override_settings(DEBUG=True)
    def test_crash_is_json_even_with_debug_on(self):
        with mock.patch.object(views.MeView, "get", side_effect=KeyError("x")):
            with self.assertLogs("core.exceptions", level="ERROR"):
                res = self.client.get("/api/me/")
        self.assert_json_error(res, 500, SERVER_ERROR)

    def test_crash_during_question_create_is_json_500(self):
        mentee, token = make_user("maria@t.com", "Maria Lopez", "mentee")
        with mock.patch("core.views.question_queryset", side_effect=RuntimeError("boom")):
            with self.assertLogs("core.exceptions", level="ERROR"):
                res = client_for(token).post(
                    "/api/questions/", {"text": "How do I break into UX design?"}, format="json"
                )
        self.assert_json_error(res, 500, SERVER_ERROR)

    def test_500_still_has_cors_headers(self):
        with mock.patch.object(views.InboxView, "get", side_effect=RuntimeError("boom")):
            with self.assertLogs("core.exceptions", level="ERROR"):
                res = self.client.get("/api/inbox/", HTTP_ORIGIN=FRONTEND)
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res["Access-Control-Allow-Origin"], FRONTEND)

    def test_unknown_api_path_is_json_404(self):
        self.assert_json_error(self.client.get("/api/does-not-exist/"), 404, "Not found.")

    @override_settings(DEBUG=True)
    def test_unknown_api_path_is_json_404_with_debug_on(self):
        self.assert_json_error(self.client.get("/api/does-not-exist/"), 404, "Not found.")

    def test_existing_json_errors_are_unchanged(self):
        self.assertEqual(APIClient().get("/api/me/").json(), {"detail": "Authentication credentials were not provided."})
        res = self.client.post("/api/matches/999999/answer/", {"text": "hi"}, format="json")
        self.assert_json_error(res, 404, "Not found.")
        res = self.client.post("/api/questions/", {"text": "How do I break into UX?"}, format="json")
        self.assert_json_error(res, 403, "Only mentees can ask questions.")
        res = self.client.delete("/api/me/")
        self.assertEqual(res.status_code, 405)
        self.assertIn("detail", res.json())

    def test_non_api_paths_are_untouched(self):
        res = Client().get("/not-api/")
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res["Content-Type"].startswith("application/json"))
        self.assertEqual(Client().get("/api/docs/").status_code, 200)  # HTML docs page is a 200, left alone


@FAST_HASHER
@override_settings(DEBUG=True)  # DEBUG is where a slash-less POST used to raise (APPEND_SLASH RuntimeError)
class MissingSlashTests(TestCase):
    def test_post_without_trailing_slash_works(self):
        res = APIClient().post(
            "/api/signup", {"email": "x@t.com", "password": "secret1", "full_name": "X Y", "role": "mentee"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        token = res.json()["token"]
        self.assertEqual(client_for(token).get("/api/me").status_code, 200)  # GET: no 301 redirect either

    def test_route_with_id_without_slash(self):
        _, token = make_user("maya@t.com", "Maya Chen", "mentor")
        res = client_for(token).post("/api/matches/999/answer", {"text": "hi"}, format="json")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json(), {"detail": "Not found."})  # the view's 404, so the route did resolve

    def test_unknown_path_without_slash_is_still_json_404(self):
        res = Client().get("/api/nothing-here")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json(), {"detail": "Not found."})


@override_settings(ROOT_URLCONF="core.tests.test_hardening")
class PlainViewErrorTests(TestCase):
    def test_crash_outside_drf_is_json_500(self):
        client = Client(raise_request_exception=False)
        with self.assertLogs("django.request", level="ERROR"):
            res = client.get("/api/test-crash/", HTTP_ORIGIN=FRONTEND)
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.json(), {"detail": SERVER_ERROR})
        self.assertEqual(res["Access-Control-Allow-Origin"], FRONTEND)

    @override_settings(DEBUG=True)
    def test_crash_outside_drf_with_debug_is_json_500(self):
        client = Client(raise_request_exception=False)
        with self.assertLogs("django.request", level="ERROR"):
            res = client.get("/api/test-crash/")
        self.assertEqual(res.json(), {"detail": SERVER_ERROR})

    def test_html_error_under_api_becomes_json(self):
        with self.assertLogs("django.request", level="WARNING"):
            res = Client().get("/api/test-html-400/")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), {"detail": "Bad Request."})


class CorsTests(TestCase):
    def test_preflight_for_post_questions_from_vite(self):
        res = Client().options(
            "/api/questions/",
            HTTP_ORIGIN=FRONTEND,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Access-Control-Allow-Origin"], FRONTEND)
        self.assertIn("POST", res["Access-Control-Allow-Methods"])
        allowed = res["Access-Control-Allow-Headers"].lower()
        self.assertIn("authorization", allowed)
        self.assertIn("content-type", allowed)

    def test_127_origin_allowed_unknown_origin_not(self):
        ok = Client().get("/api/health/", HTTP_ORIGIN="http://127.0.0.1:5173")
        self.assertEqual(ok["Access-Control-Allow-Origin"], "http://127.0.0.1:5173")
        bad = Client().get("/api/health/", HTTP_ORIGIN="https://evil.example")
        self.assertNotIn("Access-Control-Allow-Origin", bad)


class StartupNoticeTests(TestCase):
    def notice(self, **env):
        keys = ["LLM_PROVIDER", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_MODEL", "OPENAI_MODEL"]
        clean = {k: env.get(k, "") for k in keys}
        with mock.patch.dict(os.environ, clean):
            with self.assertLogs("core.matching", level="INFO") as logs:
                message = matching.log_startup_status()
        return message, logs.records[-1].levelname

    def test_no_key_warns_keyword_fallback(self):
        message, level = self.notice(LLM_PROVIDER="anthropic")
        self.assertEqual(level, "WARNING")
        self.assertIn("ANTHROPIC_API_KEY is empty", message)
        self.assertIn("Using keyword fallback for matching", message)

    def test_provider_none_warns(self):
        message, level = self.notice(LLM_PROVIDER="none")
        self.assertEqual(level, "WARNING")
        self.assertIn("Using keyword fallback for matching", message)

    def test_unknown_provider_warns(self):
        message, level = self.notice(LLM_PROVIDER="gemini", OPENAI_API_KEY="sk-x")
        self.assertEqual(level, "WARNING")
        self.assertIn("Using keyword fallback for matching", message)

    def test_key_set_is_info_with_model_and_timeout(self):
        message, level = self.notice(LLM_PROVIDER="openai", OPENAI_API_KEY="sk-test")
        self.assertEqual(level, "INFO")
        self.assertIn("openai (gpt-4o-mini)", message)
        self.assertIn(f"{matching.LLM_TIMEOUT_SECONDS:g}s timeout", message)
        self.assertNotIn("sk-test", message)  # never log the key
