from django.urls import path

from . import views

# Mounted under /api/ in connecther/urls.py.
urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("me/", views.MeView.as_view(), name="me"),
    path("mentor-profile/", views.MentorProfileView.as_view(), name="mentor-profile"),
    path("mentors/", views.MentorListView.as_view(), name="mentors"),
    path("questions/", views.QuestionCreateView.as_view(), name="questions"),
    path("questions/mine/", views.MyQuestionsView.as_view(), name="questions-mine"),
    path("inbox/", views.InboxView.as_view(), name="inbox"),
    path("matches/<int:match_id>/answer/", views.AnswerCreateView.as_view(), name="match-answer"),
]
