from django.contrib import admin

from .models import Answer, MentorProfile, Profile, Question, QuestionMatch

for model in (Profile, MentorProfile, Question, QuestionMatch, Answer):
    admin.site.register(model)
