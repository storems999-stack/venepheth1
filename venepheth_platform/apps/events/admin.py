from django.contrib import admin

from .models import Event


@admin.action(description="Publish selected events")
def make_published(modeladmin, request, queryset):
    from django.utils import timezone

    count = queryset.update(status="published", published_at=timezone.now())
    modeladmin.message_user(request, f"{count} event(s) successfully marked as published.")


@admin.action(description="Archive selected events")
def make_archived(modeladmin, request, queryset):
    count = queryset.update(status="archived")
    modeladmin.message_user(request, f"{count} event(s) successfully archived.")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "start_time", "status")
    list_filter = ("event_type", "status", "is_virtual")
    search_fields = ("title", "location")
    actions = [make_published, make_archived]
    prepopulated_fields = {"slug": ("title",)}
