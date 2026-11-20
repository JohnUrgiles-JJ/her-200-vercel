from rest_framework import serializers

from .models import Answer, MentorProfile, Profile, Question, QuestionMatch


def serialize_user(user):
    """The `User` shape from Section 3.1. Used everywhere a user is returned."""
    profile = getattr(user, "profile", None)  # None for e.g. the admin superuser
    return {
        "id": user.id,
        "email": user.email,
        "full_name": profile.full_name if profile else (user.get_full_name() or user.username),
        "role": profile.role if profile else None,
        "has_mentor_profile": MentorProfile.objects.filter(user=user).exists(),
    }


# --- Auth --------------------------------------------------------------------


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=150)  # User.username is max 150 chars
    password = serializers.CharField(min_length=6, max_length=128, write_only=True, trim_whitespace=False)
    full_name = serializers.CharField(max_length=120)
    role = serializers.ChoiceField(choices=[c[0] for c in Profile.ROLE_CHOICES])

    def validate_email(self, value):
        return value.strip().lower()


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class UserSerializer(serializers.Serializer):
    """Documents the `User` shape for the API schema. Responses are built with serialize_user()."""

    id = serializers.IntegerField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    role = serializers.CharField(allow_null=True)
    has_mentor_profile = serializers.BooleanField()


class AuthResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = UserSerializer()


# --- Mentor profile ----------------------------------------------------------


class CommaListField(serializers.Field):
    """Accepts "a, b, c" or ["a", "b", "c"] and stores the normalized string "a, b, c"."""

    default_error_messages = {
        "invalid": "Must be a comma-separated string or a list of strings.",
        "blank": "This field may not be blank.",
        "max_length": "Ensure this field has no more than {max_length} characters.",
    }

    def __init__(self, max_length=None, **kwargs):
        self.max_length = max_length
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str):
            items = data.split(",")
        elif isinstance(data, (list, tuple)) and all(isinstance(i, str) for i in data):
            # A list item may itself contain commas ("UX, Figma"); split those too.
            items = [part for item in data for part in item.split(",")]
        else:
            self.fail("invalid")
        value = ", ".join(i.strip() for i in items if i.strip())
        if not value:
            self.fail("blank")
        if self.max_length is not None and len(value) > self.max_length:
            self.fail("max_length", max_length=self.max_length)
        return value

    def to_representation(self, value):
        return value


class MentorProfileSerializer(serializers.ModelSerializer):
    fields = CommaListField(max_length=300)
    open_to = CommaListField(max_length=300)

    class Meta:
        model = MentorProfile
        fields = ["headline", "company", "fields", "open_to", "bio", "experience_years"]


class MentorListItemSerializer(serializers.ModelSerializer):
    mentor_id = serializers.IntegerField(source="user_id", read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = MentorProfile
        fields = ["mentor_id", "name", "headline", "company", "fields", "open_to", "bio", "experience_years"]

    def get_name(self, obj) -> str:
        profile = getattr(obj.user, "profile", None)
        return profile.full_name if profile else (obj.user.get_full_name() or obj.user.username)


# --- Questions and matches ---------------------------------------------------


def _display_name(user):
    profile = getattr(user, "profile", None)
    return profile.full_name if profile else (user.get_full_name() or user.username)


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["id", "text", "created_at"]


class MatchSerializer(serializers.ModelSerializer):
    """The `Match` shape from Section 3.1. Expects mentor__profile, mentor__mentor_profile and answers
    to be prefetched (see question_queryset in views.py)."""

    match_id = serializers.IntegerField(source="id", read_only=True)
    mentor_id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    headline = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = QuestionMatch
        fields = ["match_id", "mentor_id", "name", "headline", "company", "reason", "rank", "status", "answers"]

    def get_name(self, obj) -> str:
        return _display_name(obj.mentor)

    def _mentor_profile(self, obj):
        # RelatedObjectDoesNotExist is an AttributeError, so a deleted MentorProfile gives None.
        return getattr(obj.mentor, "mentor_profile", None)

    def get_headline(self, obj) -> str:
        mp = self._mentor_profile(obj)
        return mp.headline if mp else ""

    def get_company(self, obj) -> str:
        mp = self._mentor_profile(obj)
        return mp.company if mp else ""


class QuestionSerializer(serializers.ModelSerializer):
    """The `Question` shape from Section 3.1. Matches come out in rank order."""

    matches = MatchSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "created_at", "matches"]


class QuestionCreateSerializer(serializers.Serializer):
    """Documents the POST /questions/ body for the API schema. Validation is done in the view."""

    text = serializers.CharField(min_length=10, max_length=1000)
