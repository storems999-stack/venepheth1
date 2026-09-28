"""Courses app URL configuration."""

from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.course_list, name="list"),
    path("resource/<int:pk>/download/", views.course_resource_download, name="resource_download"),
    path("<slug:slug>/", views.course_detail, name="detail"),
]
