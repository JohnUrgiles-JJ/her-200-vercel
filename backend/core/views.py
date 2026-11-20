from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import notify
from .matching import match_mentors
from .models import Answer, MentorProfile, Profile, Question, QuestionMatch
from .serializers import (
    AnswerSerializer, InboxSerializer, LoginSerializer, MentorProfileSerializer,
    QuestionSerializer, SignupSerializer,
)


def _user_payload(user):
    return {"id": user.id, "full_name": user.profile.full_name, "role": user.profile.role}


def _forbidden_unless(user, role):
    if user.profile.role != role:
        return Response({"detail": f"Only {role}s can do this."}, status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    s = SignupSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    email = s.validated_data["email"].lower()
    if User.objects.filter(username=email).exists():
        return Response({"email": ["An account with this email already exists."]}, status=400)
    with transaction.atomic():
        user = User.objects.create_user(username=email, email=email, password=s.validated_data["password"])
        Profile.objects.create(user=user, full_name=s.validated_data["full_name"], role=s.validated_data["role"])
        token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": _user_payload(user)}, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    s = LoginSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = authenticate(username=s.validated_data["email"].lower(), password=s.validated_data["password"])
    if user is None:
        return Response({"detail": "Invalid email or password."}, status=400)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": _user_payload(user)})


@api_view(["GET"])
def me(request):
    return Response({
        **_user_payload(request.user),
        "has_mentor_profile": MentorProfile.objects.filter(user=request.user).exists(),
    })


@api_view(["POST", "PUT"])
def mentor_profile(request):
    if denied := _forbidden_unless(request.user, Profile.MENTOR):
        return denied
    existing = MentorProfile.objects.filter(user=request.user).first()
    s = MentorProfileSerializer(existing, data=request.data)
    s.is_valid(raise_exception=True)
    s.save(user=request.user)
    return Response(s.data, status=200 if existing else 201)


@api_view(["GET"])
def mentors(request):
    qs = MentorProfile.objects.select_related("user__profile").order_by("-experience_years")
    return Response(MentorProfileSerializer(qs, many=True).data)


@api_view(["POST"])
def ask_question(request):
    if denied := _forbidden_unless(request.user, Profile.MENTEE):
        return denied
    text = str(request.data.get("text", "")).strip()
    if not text:
        return Response({"text": ["This field is required."]}, status=400)

    question = Question.objects.create(mentee=request.user, text=text)
    picks = match_mentors(text)
    matches = [
        QuestionMatch.objects.create(question=question, mentor_id=p["mentor_id"], reason=p["reason"])
        for p in picks
    ]
    mentee_name = request.user.profile.full_name
    for m in matches:
        notify.push(m.mentor_id, {"type": "new_question", "match": InboxSerializer(m).data})
    for m in matches:
        notify.email(
            m.mentor.email,
            f"New question from {mentee_name} on ConnectHER",
            f"{mentee_name} asked:\n\n{text}\n\nWhy you: {m.reason}\n\n"
            f"Answer it from your inbox: {settings.FRONTEND_URL}/main",
        )
    return Response(QuestionSerializer(question).data, status=201)


@api_view(["GET"])
def my_questions(request):
    if denied := _forbidden_unless(request.user, Profile.MENTEE):
        return denied
    qs = Question.objects.filter(mentee=request.user).prefetch_related(
        "matches__mentor__profile", "matches__mentor__mentor_profile"
    )
    return Response(QuestionSerializer(qs, many=True).data)


@api_view(["GET"])
def inbox(request):
    if denied := _forbidden_unless(request.user, Profile.MENTOR):
        return denied
    qs = QuestionMatch.objects.filter(mentor=request.user).select_related("question__mentee__profile", "answer")
    return Response(InboxSerializer(qs, many=True).data)


@api_view(["POST"])
def answer_match(request, match_id):
    if denied := _forbidden_unless(request.user, Profile.MENTOR):
        return denied
    match = get_object_or_404(QuestionMatch, id=match_id, mentor=request.user)
    text = str(request.data.get("text", "")).strip()
    if not text:
        return Response({"text": ["This field is required."]}, status=400)
    if hasattr(match, "answer"):
        return Response({"detail": "You've already answered this question."}, status=400)
    answer = Answer.objects.create(match=match, text=text)
    match.status = QuestionMatch.ANSWERED
    match.save(update_fields=["status"])
    data = AnswerSerializer(answer).data
    notify.push(match.question.mentee_id, {"type": "new_answer", "answer": data})
    return Response(data, status=201)
