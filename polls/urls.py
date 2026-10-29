from django.urls import path

from . import views

app_name = "polls"

urlpatterns = [
    path("", views.poll_list, name="list"),
    path("polls/new/", views.poll_create, name="create"),
    path("polls/<int:pk>/", views.poll_detail, name="detail"),
    path("polls/<int:pk>/vote/", views.vote, name="vote"),
    path("polls/<int:pk>/delete/", views.poll_delete, name="delete"),
]
