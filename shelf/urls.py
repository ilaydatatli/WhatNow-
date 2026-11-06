from django.urls import path

from . import views

app_name = "shelf"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("top/", views.top, name="top"),
    path("quiz/", views.quiz, name="quiz"),
    path("items/new/", views.item_create, name="item_create"),
    path("items/search/", views.item_search, name="item_search"),
    path("items/<int:pk>/", views.item_detail, name="item_detail"),
    path("items/<int:pk>/add/", views.item_add, name="item_add"),
    path("shelf/<int:pk>/edit/", views.entry_edit, name="entry_edit"),
    path("u/<str:username>/", views.user_shelf, name="user_shelf"),
    path("shelf/<int:pk>/remove/", views.entry_remove, name="entry_remove"),
]
