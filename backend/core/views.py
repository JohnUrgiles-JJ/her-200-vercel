import logging

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.models import Prefetch, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import matching, notify
from .models import Answer, MentorProfile, Profile, Question, QuestionMatch
from .permissions import IsMentee, IsMentor
from .serializers import (
    AnswerCreateSerializer,
    AnswerSerializer,
    AuthResponseSerializer,
    CommunityQuestionSerializer,
    InboxItemSerializer,
    LoginSerializer,
    MentorListItemSerializer,
    MentorProfileSerializer,
    QuestionCreateSerializer,
    QuestionSerializer,
    QuestionVisibilitySerializer,
    SignupSerializer,
    UserSerializer,
    serialize_user,
)

logger = logging.getLogger(__name__)

DUPLICATE_EMAIL = "An account with this email already exists."
INVALID_LOGIN = "Invalid email or password."
NO_MENTOR_PROFILE = "Mentor profile not found."
QUESTION_MIN, QUESTION_MAX = 10, 1000
QUESTION_REQUIRED = "Question text is required."
QUESTION_LENGTH = f"Question must be between {QUESTION_MIN} and {QUESTION_MAX} characters."
ANSWER_MAX = 3000
ANSWER_REQUIRED = "Answer text is required."
ANSWER_LENGTH = f"Answer must be at most {ANSWER_MAX} characters."
INBOX_STATUSES = sorted(c[0] for c in QuestionMatch.STATUS)
INBOX_BAD_STATUS = "status must be one of: answered, sent."
NOT_FOUND = "Not found."
IS_PUBLIC_BOOL = "is_public must be true or false."
COMMUNITY_LIMIT = 50


class HealthView(APIView):
    """Public health check for Railway. Always 200; "db" shows whether SELECT 1 works."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: {"type": "object", "properties": {"status": {"type": "string"}, "db": {"type": "boolean"}}}})
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            db_ok = True
        except DatabaseError:
            logger.exception("Health check: database query failed")
            db_ok = False
        return Response({"status": "ok", "db": db_ok})


class SignupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # a stale token header must not block signup

    @extend_schema(request=SignupSerializer, responses={201: AuthResponseSerializer})
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data["email"]

        if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            return Response({"detail": DUPLICATE_EMAIL}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                user = User(username=email, email=email)
                user.set_password(data["password"])
                user.save()
                Profile.objects.create(user=user, role=data["role"], full_name=data["full_name"])
                token = Token.objects.create(user=user)
        except IntegrityError:  # two signups with the same email at the same time
            return Response({"detail": DUPLICATE_EMAIL}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"token": token.key, "user": serialize_user(user)}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=LoginSerializer, responses={200: AuthResponseSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"].strip().lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": INVALID_LOGIN}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": serialize_user(user)})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(serialize_user(request.user))


class MentorProfileView(APIView):
    permission_classes = [IsAuthenticated, IsMentor]

    @extend_schema(responses={200: MentorProfileSerializer})
    def get(self, request):
        profile = MentorProfile.objects.filter(user=request.user).first()
        if profile is None:
            return Response({"detail": NO_MENTOR_PROFILE}, status=status.HTTP_404_NOT_FOUND)
        return Response(MentorProfileSerializer(profile).data)

    @extend_schema(request=MentorProfileSerializer, responses={200: MentorProfileSerializer})
    def post(self, request):
        """Create or update the requesting mentor's profile."""
        existing = MentorProfile.objects.filter(user=request.user).first()
        serializer = MentorProfileSerializer(existing, data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user=request.user)
        return Response(MentorProfileSerializer(profile).data)

    @extend_schema(request=MentorProfileSerializer, responses={200: MentorProfileSerializer})
    def put(self, request):
        """Same as POST: create or update."""
        return self.post(request)


class MentorListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MentorListItemSerializer(many=True)})
    def get(self, request):
        mentors = (
            MentorProfile.objects.filter(is_active=True, user__is_active=True)
            .select_related("user", "user__profile")
            .order_by("user_id")
        )
        return Response(MentorListItemSerializer(mentors, many=True).data)


# --- Questions ---------------------------------------------------------------


def question_queryset():
    """Questions with everything the Question shape needs, in a fixed number of queries."""
    matches = QuestionMatch.objects.select_related("mentor__profile", "mentor__mentor_profile").prefetch_related(
        "answers"
    ).order_by("rank")
    return Question.objects.prefetch_related(Prefetch("matches", queryset=matches))


def _notify_safely(question, matches):
    try:
        notify.notify_matched_mentors(question, matches)
    except Exception:
        logger.exception("notify_matched_mentors failed for question %s", question.id)


class QuestionCreateView(APIView):
    permission_classes = [IsAuthenticated, IsMentee]

    @extend_schema(request=QuestionCreateSerializer, responses={201: QuestionSerializer})
    def post(self, request):
        text = request.data.get("text") if hasattr(request.data, "get") else None
        if not isinstance(text, str) or not text.strip():
            return Response({"detail": QUESTION_REQUIRED}, status=status.HTTP_400_BAD_REQUEST)
        text = text.strip()
        if not QUESTION_MIN <= len(text) <= QUESTION_MAX:
            return Response({"detail": QUESTION_LENGTH}, status=status.HTTP_400_BAD_REQUEST)
        is_public = request.data.get("is_public", False)
        if not isinstance(is_public, bool):
            return Response({"detail": IS_PUBLIC_BOOL}, status=status.HTTP_400_BAD_REQUEST)

        # Match before opening the transaction: the LLM call can take up to ~10 s and must not hold
        # a database write lock (SQLite locks the whole file) while it runs.
        try:
            results = matching.match_mentors(text, k=3)
        except Exception:  # match_mentors already falls back internally; this is a last resort
            logger.exception("match_mentors raised; saving the question with no matches")
            results = []

        with transaction.atomic():
            question = Question.objects.create(mentee=request.user, text=text, is_public=is_public)
            matches = [
                QuestionMatch.objects.create(
                    question=question, mentor_id=r["mentor_id"], reason=r["reason"][:200], rank=rank
                )
                for rank, r in enumerate(results, start=1)
            ]
            transaction.on_commit(lambda: _notify_safely(question, matches))

        question = question_queryset().get(pk=question.pk)
        return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)


class MyQuestionsView(APIView):
    permission_classes = [IsAuthenticated, IsMentee]

    @extend_schema(responses={200: QuestionSerializer(many=True)})
    def get(self, request):
        questions = question_queryset().filter(mentee=request.user).order_by("-created_at", "-id")
        return Response(QuestionSerializer(questions, many=True).data)


class QuestionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsMentee]

    @extend_schema(request=QuestionVisibilitySerializer, responses={200: QuestionSerializer})
    def patch(self, request, question_id):
        """Share a question on the community feed, or make it private again. Owner only."""
        if not Question.objects.filter(pk=question_id, mentee=request.user).exists():
            return Response({"detail": NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        is_public = request.data.get("is_public") if hasattr(request.data, "get") else None
        if not isinstance(is_public, bool):
            return Response({"detail": IS_PUBLIC_BOOL}, status=status.HTTP_400_BAD_REQUEST)
        Question.objects.filter(pk=question_id).update(is_public=is_public)
        return Response(QuestionSerializer(question_queryset().get(pk=question_id)).data)


def community_queryset():
    """Public questions with their answered matches, in a fixed number of queries."""
    answered = (
        QuestionMatch.objects.filter(status="answered")
        .select_related("mentor__profile", "mentor__mentor_profile")
        .prefetch_related("answers")
        .order_by("rank")
    )
    return (
        Question.objects.filter(is_public=True)
        .select_related("mentee__profile")
        .prefetch_related(Prefetch("matches", queryset=answered))
        .order_by("-created_at", "-id")
    )


class CommunityQuestionsView(APIView):
    """The community feed: other mentees' public questions and the mentor answers they got.
    Open to mentors and mentees; your own questions are left out (they're under /questions/mine/)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CommunityQuestionSerializer(many=True)})
    def get(self, request):
        questions = community_queryset().exclude(mentee=request.user)[:COMMUNITY_LIMIT]
        return Response(CommunityQuestionSerializer(questions, many=True).data)


# --- Mentor inbox and answers ------------------------------------------------


def inbox_queryset(mentor):
    """The mentor's matches with everything the InboxItem shape needs, in a fixed number of queries."""
    return (
        QuestionMatch.objects.filter(mentor=mentor)
        .select_related("question__mentee__profile")
        .prefetch_related("answers")
        .order_by("-question__created_at", "-question_id")
    )


class InboxView(APIView):
    permission_classes = [IsAuthenticated, IsMentor]

    @extend_schema(
        parameters=[OpenApiParameter("status", str, enum=INBOX_STATUSES, required=False)],
        responses={200: InboxItemSerializer(many=True)},
    )
    def get(self, request):
        matches = inbox_queryset(request.user)
        wanted = request.query_params.get("status")
        if wanted:
            if wanted not in INBOX_STATUSES:
                return Response({"detail": INBOX_BAD_STATUS}, status=status.HTTP_400_BAD_REQUEST)
            matches = matches.filter(status=wanted)
        return Response(InboxItemSerializer(matches, many=True).data)


def _notify_answer_safely(answer):
    try:
        notify.notify_mentee_of_answer(answer)
    except Exception:
        logger.exception("notify_mentee_of_answer failed for answer %s", answer.id)


class AnswerCreateView(APIView):
    permission_classes = [IsAuthenticated, IsMentor]

    @extend_schema(request=AnswerCreateSerializer, responses={201: AnswerSerializer})
    def post(self, request, match_id):
        # Ownership first: another mentor's match is a plain 404, same as a missing one, whatever the body.
        match = (
            QuestionMatch.objects.select_related("question__mentee", "mentor__profile")
            .filter(pk=match_id, mentor=request.user)
            .first()
        )
        if match is None:
            return Response({"detail": NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        text = request.data.get("text") if hasattr(request.data, "get") else None
        if not isinstance(text, str) or not text.strip():
            return Response({"detail": ANSWER_REQUIRED}, status=status.HTTP_400_BAD_REQUEST)
        text = text.strip()
        if len(text) > ANSWER_MAX:
            return Response({"detail": ANSWER_LENGTH}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            answer = Answer.objects.create(match=match, text=text)
            # A plain UPDATE (no read-modify-write), so concurrent answers can't race. Idempotent.
            QuestionMatch.objects.filter(pk=match.pk).update(status="answered")
            match.status = "answered"
            transaction.on_commit(lambda: _notify_answer_safely(answer))

        return Response(AnswerSerializer(answer).data, status=status.HTTP_201_CREATED)
