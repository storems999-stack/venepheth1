"""Teaching app URL configuration."""

from django.urls import path

from . import views

app_name = "teaching"

urlpatterns = [
    path("", views.teaching_overview, name="overview"),
]
