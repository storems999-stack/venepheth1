from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'result', 'ip_address')
    list_filter = ('action', 'result', 'timestamp')
    search_fields = ('user__email', 'description', 'ip_address')
    readonly_fields = ('user', 'action', 'result', 'description', 'ip_address', 'user_agent', 'request_path', 'extra_data')
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
