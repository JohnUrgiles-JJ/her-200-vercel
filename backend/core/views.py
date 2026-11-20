import logging

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MentorProfile, Profile
from .permissions import IsMentor
from .serializers import (
    AuthResponseSerializer,
    LoginSerializer,
    MentorListItemSerializer,
    MentorProfileSerializer,
    SignupSerializer,
    UserSerializer,
    serialize_user,
)

logger = logging.getLogger(__name__)

DUPLICATE_EMAIL = "An account with this email already exists."
INVALID_LOGIN = "Invalid email or password."
NO_MENTOR_PROFILE = "Mentor profile not found."


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
