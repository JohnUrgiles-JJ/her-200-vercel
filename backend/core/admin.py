from django.contrib import admin

from .models import Answer, MentorProfile, Profile, Question, QuestionMatch


def short(text, length=60):
    """Trim long text so admin list pages stay readable."""
    return text if len(text) <= length else text[: length - 1] + "…"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "role", "user")
    list_filter = ("role",)
    search_fields = ("full_name", "user__email", "user__username")


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "headline", "company", "experience_years", "is_active")
    list_filter = ("is_active",)
    search_fields = ("user__email", "headline", "company", "fields", "open_to")


class QuestionMatchInline(admin.TabularInline):
    model = QuestionMatch
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "short_text", "mentee", "created_at")
    search_fields = ("text", "mentee__email")
    inlines = [QuestionMatchInline]

    @admin.display(description="Text")
    def short_text(self, obj):
        return short(obj.text)


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0


@admin.register(QuestionMatch)
class QuestionMatchAdmin(admin.ModelAdmin):
    list_display = ("id", "question_id", "mentor", "rank", "status", "reason")
    list_filter = ("status",)
    search_fields = ("mentor__email", "question__text", "reason")
    inlines = [AnswerInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "match", "short_text", "created_at")
    search_fields = ("text",)

    @admin.display(description="Text")
    def short_text(self, obj):
        return short(obj.text)
