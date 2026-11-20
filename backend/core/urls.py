from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.signup),
    path("login/", views.login),
    path("me/", views.me),
    path("mentor-profile/", views.mentor_profile),
    path("mentors/", views.mentors),
    path("questions/", views.ask_question),
    path("questions/mine/", views.my_questions),
    path("inbox/", views.inbox),
    path("matches/<int:match_id>/answer/", views.answer_match),
]
