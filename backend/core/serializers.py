from rest_framework import serializers

from .models import Answer, MentorProfile, Question, QuestionMatch


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    full_name = serializers.CharField(max_length=200)
    role = serializers.ChoiceField(choices=["mentor", "mentee"])


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class MentorProfileSerializer(serializers.ModelSerializer):
    mentor_id = serializers.IntegerField(source="user_id", read_only=True)
    name = serializers.CharField(source="user.profile.full_name", read_only=True)
    fields = serializers.ListField(child=serializers.CharField(max_length=100))
    open_to = serializers.ListField(child=serializers.CharField(max_length=100))

    class Meta:
        model = MentorProfile
        fields = ["mentor_id", "name", "headline", "company", "fields", "open_to", "bio", "experience_years"]


class AnswerSerializer(serializers.ModelSerializer):
    match_id = serializers.IntegerField(source="match.id", read_only=True)
    question_id = serializers.IntegerField(source="match.question_id", read_only=True)
    mentor_id = serializers.IntegerField(source="match.mentor_id", read_only=True)
    mentor_name = serializers.CharField(source="match.mentor.profile.full_name", read_only=True)

    class Meta:
        model = Answer
        fields = ["id", "match_id", "question_id", "mentor_id", "mentor_name", "text", "created_at"]


class MatchSerializer(serializers.ModelSerializer):
    mentor_id = serializers.IntegerField(source="mentor.id")
    name = serializers.CharField(source="mentor.profile.full_name")
    headline = serializers.CharField(source="mentor.mentor_profile.headline")

    class Meta:
        model = QuestionMatch
        fields = ["mentor_id", "name", "headline", "reason"]


class QuestionSerializer(serializers.ModelSerializer):
    matches = MatchSerializer(many=True, read_only=True)
    answers = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ["id", "text", "created_at", "matches", "answers"]

    def get_answers(self, q):
        return AnswerSerializer(Answer.objects.filter(match__question=q).order_by("created_at"), many=True).data


class InboxSerializer(serializers.ModelSerializer):
    match_id = serializers.IntegerField(source="id")
    question_text = serializers.CharField(source="question.text")
    mentee_name = serializers.CharField(source="question.mentee.profile.full_name")
    answer = serializers.SerializerMethodField()

    class Meta:
        model = QuestionMatch
        fields = ["match_id", "question_text", "mentee_name", "reason", "status", "created_at", "answer"]

    def get_answer(self, m):
        return m.answer.text if hasattr(m, "answer") else None
