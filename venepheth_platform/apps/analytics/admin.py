from django.contrib import admin
from .models import PageView

@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ('path', 'timestamp', 'ip_address', 'is_authenticated')
    list_filter = ('is_authenticated', 'timestamp')
    search_fields = ('path', 'ip_address')
    readonly_fields = ('path', 'timestamp', 'ip_address', 'user_agent', 'referer', 'is_authenticated')
