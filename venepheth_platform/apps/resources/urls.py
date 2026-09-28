"""Resources URLs."""

from django.urls import path

from . import views

app_name = "resources"

urlpatterns = [
    path("", views.resource_list, name="list"),
    path("<slug:slug>/", views.resource_detail, name="detail"),
]
