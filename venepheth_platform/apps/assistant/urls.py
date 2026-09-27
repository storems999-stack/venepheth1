"""URL configuration for AI Academic Assistant."""
from django.urls import path
from . import views

app_name = "assistant"

urlpatterns = [
    path("", views.assistant_page, name="chat"),
    path("chat/", views.assistant_chat, name="api_chat"),
]
