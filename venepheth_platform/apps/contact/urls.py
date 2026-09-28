"""Contact app URL configuration."""

from django.urls import path

from . import views

app_name = "contact"

urlpatterns = [
    path("", views.contact_form, name="form"),
    path("success/", views.contact_success, name="success"),
]
