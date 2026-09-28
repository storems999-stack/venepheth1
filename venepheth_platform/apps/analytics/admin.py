from django.contrib import admin

from .models import PageView


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ("path", "timestamp", "ip_address", "is_authenticated")
    list_filter = ("is_authenticated", "timestamp")
    search_fields = ("path", "ip_address")
    readonly_fields = ("path", "timestamp", "ip_address", "user_agent", "referer", "is_authenticated")

    def has_add_permission(self, request):
        # Analytics history is written by the system only.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
