from django.conf import settings
from django.db import models


class Profile(models.Model):
    MENTOR, MENTEE = "mentor", "mentee"
    ROLES = [(MENTOR, "Mentor"), (MENTEE, "Mentee")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=200)
    role = models.CharField(max_length=10, choices=ROLES)


class MentorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentor_profile")
    headline = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    fields = models.JSONField(default=list)
    open_to = models.JSONField(default=list)
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)


class Question(models.Model):
    mentee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class QuestionMatch(models.Model):
    PENDING, ANSWERED = "pending", "answered"
    STATUSES = [(PENDING, "Pending"), (ANSWERED, "Answered")]

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="matches")
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="matches")
    reason = models.CharField(max_length=300)
    status = models.CharField(max_length=10, choices=STATUSES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("question", "mentor")]


class Answer(models.Model):
    match = models.OneToOneField(QuestionMatch, on_delete=models.CASCADE, related_name="answer")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
