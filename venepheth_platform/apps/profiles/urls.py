"""Profile URLs."""
from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.profile_detail, name="detail"),
    path("cv/", views.cv_print, name="cv_print"),
]
