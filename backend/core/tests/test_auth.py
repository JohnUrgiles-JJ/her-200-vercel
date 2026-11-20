from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from core.models import MentorProfile, Profile

PROFILE_BODY = {
    "headline": "UX Designer",
    "company": "Figma",
    "fields": "UX, Figma, user research",
    "open_to": "career switching, portfolios",
    "bio": "Switched from teaching to UX.",
    "experience_years": 6,
}


def signup(client, email="maria@demo.com", password="secret123", full_name="Maria Lopez", role="mentee"):
    return client.post(
        "/api/signup/",
        {"email": email, "password": password, "full_name": full_name, "role": role},
        format="json",
    )


def authed_client(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


class SignupTests(APITestCase):
    def test_signup_success(self):
        res = signup(self.client, email="  Maria@Demo.COM ")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["token"])
        self.assertEqual(
            res.data["user"],
            {
                "id": res.data["user"]["id"],
                "email": "maria@demo.com",
                "full_name": "Maria Lopez",
                "role": "mentee",
                "has_mentor_profile": False,
            },
        )
        user = User.objects.get(username="maria@demo.com")
        self.assertEqual(user.email, "maria@demo.com")
        self.assertTrue(user.check_password("secret123"))
        self.assertEqual(user.profile.role, "mentee")
        self.assertEqual(Token.objects.get(user=user).key, res.data["token"])

    def test_duplicate_email(self):
        signup(self.client)
        res = signup(self.client, email="MARIA@demo.com")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data, {"detail": "An account with this email already exists."})
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_role(self):
        res = signup(self.client, role="admin")
        self.assertEqual(res.status_code, 400)
        self.assertIn("role", res.data)
        self.assertFalse(User.objects.exists())

    def test_short_password_invalid_email_missing_name(self):
        self.assertIn("password", signup(self.client, password="12345").data)
        self.assertIn("email", signup(self.client, email="not-an-email").data)
        self.assertIn("full_name", signup(self.client, full_name="").data)
        self.assertFalse(User.objects.exists())


class LoginTests(APITestCase):
    def setUp(self):
        self.signup_token = signup(self.client).data["token"]

    def test_login_success(self):
        res = self.client.post("/api/login/", {"email": "Maria@Demo.com", "password": "secret123"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["token"], self.signup_token)
        self.assertEqual(res.data["user"]["email"], "maria@demo.com")

    def test_login_wrong_password(self):
        res = self.client.post("/api/login/", {"email": "maria@demo.com", "password": "wrong-pass"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data, {"detail": "Invalid email or password."})

    def test_login_unknown_email(self):
        res = self.client.post("/api/login/", {"email": "nobody@demo.com", "password": "secret123"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data, {"detail": "Invalid email or password."})


class MeTests(APITestCase):
    def test_me_with_token(self):
        token = signup(self.client).data["token"]
        res = authed_client(token).get("/api/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["email"], "maria@demo.com")
        self.assertEqual(res.data["role"], "mentee")

    def test_me_without_token(self):
        self.assertEqual(self.client.get("/api/me/").status_code, 401)

    def test_me_with_bad_token(self):
        self.assertEqual(authed_client("not-a-real-token").get("/api/me/").status_code, 401)


class MentorProfileTests(APITestCase):
    def setUp(self):
        self.mentor = authed_client(signup(self.client, email="maya@demo.com", full_name="Maya Chen", role="mentor").data["token"])
        self.mentee = authed_client(signup(self.client).data["token"])

    def test_get_before_create_is_404(self):
        res = self.mentor.get("/api/mentor-profile/")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data, {"detail": "Mentor profile not found."})

    def test_upsert_as_mentor(self):
        res = self.mentor.post("/api/mentor-profile/", PROFILE_BODY, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, PROFILE_BODY)
        self.assertTrue(self.mentor.get("/api/me/").data["has_mentor_profile"])

        # PUT updates the same row, and lists are normalized to a comma-separated string.
        res = self.mentor.put(
            "/api/mentor-profile/",
            {"headline": "Senior UX Designer", "fields": [" UX ", "", "Research"], "open_to": "portfolios, ,  "},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["headline"], "Senior UX Designer")
        self.assertEqual(res.data["fields"], "UX, Research")
        self.assertEqual(res.data["open_to"], "portfolios")
        self.assertEqual(MentorProfile.objects.count(), 1)
        self.assertEqual(self.mentor.get("/api/mentor-profile/").data["fields"], "UX, Research")

    def test_upsert_defaults_and_required_fields(self):
        res = self.mentor.post(
            "/api/mentor-profile/", {"headline": "PM", "fields": "product", "open_to": "interviews"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["experience_years"], 0)
        self.assertEqual(res.data["company"], "")

        res = self.mentor.post("/api/mentor-profile/", {"headline": "PM", "fields": " , "}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("fields", res.data)
        self.assertIn("open_to", res.data)

    def test_mentor_profile_as_mentee_is_403(self):
        for method in ("get", "post", "put"):
            res = getattr(self.mentee, method)("/api/mentor-profile/", PROFILE_BODY, format="json")
            self.assertEqual(res.status_code, 403, method)
            self.assertEqual(res.data, {"detail": "Only mentors can do this."})
        self.assertFalse(MentorProfile.objects.exists())

    def test_mentor_profile_without_token_is_401(self):
        self.assertEqual(APIClient().get("/api/mentor-profile/").status_code, 401)

    def test_user_without_profile_gets_403(self):
        admin = User.objects.create_superuser("admin", "admin@connecther.local", "admin1234")
        client = authed_client(Token.objects.create(user=admin).key)
        res = client.get("/api/mentor-profile/")
        self.assertEqual(res.status_code, 403)
        self.assertIn("no ConnectHER profile", res.data["detail"])
        me = client.get("/api/me/")
        self.assertEqual(me.status_code, 200)
        self.assertIsNone(me.data["role"])


class MentorListTests(APITestCase):
    def test_lists_active_mentors(self):
        mentor = authed_client(signup(self.client, email="maya@demo.com", full_name="Maya Chen", role="mentor").data["token"])
        mentor.post("/api/mentor-profile/", PROFILE_BODY, format="json")

        inactive = User.objects.create_user("old@demo.com", "old@demo.com", "secret123")
        Profile.objects.create(user=inactive, role="mentor", full_name="Old Mentor")
        MentorProfile.objects.create(user=inactive, headline="x", fields="x", open_to="x", is_active=False)

        mentee = authed_client(signup(self.client).data["token"])
        res = mentee.get("/api/mentors/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        maya = User.objects.get(username="maya@demo.com")
        self.assertEqual(res.data[0], {"mentor_id": maya.id, "name": "Maya Chen", **PROFILE_BODY})

    def test_requires_token(self):
        self.assertEqual(self.client.get("/api/mentors/").status_code, 401)
