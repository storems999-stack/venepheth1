"""Research app URL configuration."""
from django.urls import path
from . import views

app_name = "research"

urlpatterns = [
    path("", views.research_list, name="list"),
    path("project/<slug:slug>/", views.project_detail, name="project_detail"),
    path("publications/", views.publications_redirect, name="publications"),
]
