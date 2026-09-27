from django.contrib import admin
from .models import SecurityEvent

@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'severity', 'ip_address', 'timestamp', 'resolved')
    list_filter = ('severity', 'event_type', 'resolved', 'timestamp')
    search_fields = ('ip_address', 'description')
    readonly_fields = ('event_type', 'severity', 'description', 'ip_address', 'user_agent', 'request_path', 'extra_data', 'timestamp')
