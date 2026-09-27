"""
Notifications URL configuration.
"""
from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("badge/", views.unread_badge, name="unread_badge"),
    path("<int:pk>/read/", views.mark_as_read, name="mark_read"),
    path("mark-all-read/", views.mark_all_as_read, name="mark_all_read"),
]
