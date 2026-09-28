from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "message", "is_read", "created_at")
    list_filter = ("level", "is_read")
    search_fields = ("user__email", "message")
    # Notifications are created by the system; staff must not forge
    # arbitrary messages/links to users (phishing vector).
    readonly_fields = ("user", "level", "message", "link", "created_at")

    def has_add_permission(self, request):
        return False
