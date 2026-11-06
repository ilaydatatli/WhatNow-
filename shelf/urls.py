from django.urls import path

from . import views

app_name = "shelf"

urlpatterns = [
    path("", views.home, name="home"),
    path("items/new/", views.item_create, name="item_create"),
    path("items/search/", views.item_search, name="item_search"),
    path("items/<int:pk>/", views.item_detail, name="item_detail"),
    path("items/<int:pk>/add/", views.item_add, name="item_add"),
    path("shelf/<int:pk>/edit/", views.entry_edit, name="entry_edit"),
    path("shelf/<int:pk>/remove/", views.entry_remove, name="entry_remove"),
]
