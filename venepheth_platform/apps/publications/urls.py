"""Publications app URL configuration."""

from django.urls import path

from . import views

app_name = "publications"

urlpatterns = [
    path("", views.publication_list, name="list"),
    path("download/<slug:slug>/", views.publication_download, name="download"),
    path("<slug:slug>/", views.publication_detail, name="detail"),
]
