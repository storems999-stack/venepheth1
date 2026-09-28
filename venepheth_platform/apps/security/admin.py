from django.contrib import admin

from .models import SecurityEvent


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "severity", "ip_address", "timestamp", "resolved")
    list_filter = ("severity", "event_type", "resolved", "timestamp")
    search_fields = ("ip_address", "description")
    readonly_fields = (
        "event_type",
        "severity",
        "description",
        "ip_address",
        "user_agent",
        "request_path",
        "extra_data",
        "timestamp",
        "resolved_at",
    )

    def has_add_permission(self, request):
        # Security history must only be written by the system, never by staff.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
