# core/models.py
from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = [("mentor", "Mentor"), ("mentee", "Mentee")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    full_name = models.CharField(max_length=120)

class MentorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mentor_profile")
    headline = models.CharField(max_length=150)
    company = models.CharField(max_length=120, blank=True)
    fields = models.CharField(max_length=300)
    open_to = models.CharField(max_length=300)
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

class Question(models.Model):
    mentee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    # Opt-in: a public question (and its mentor answers) shows on the community feed for everyone.
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]

class QuestionMatch(models.Model):
    STATUS = [("sent", "Sent"), ("answered", "Answered")]
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="matches")
    mentor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="matches")
    reason = models.CharField(max_length=200)
    rank = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS, default="sent")
    class Meta:
        ordering = ["rank"]
        unique_together = [("question", "mentor")]

class Answer(models.Model):
    match = models.ForeignKey(QuestionMatch, on_delete=models.CASCADE, related_name="answers")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["created_at"]
