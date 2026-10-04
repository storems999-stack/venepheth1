"""Teaching app admin."""

from django.contrib import admin
from django.utils import timezone

from apps.core.admin_actions import save_queryset_with_history

from .models import OfficeHours, StudentAnnouncement, TeachingPhilosophy


@admin.register(OfficeHours)
class OfficeHoursAdmin(admin.ModelAdmin):
    list_display = ("day", "start_time", "end_time", "location", "is_virtual", "is_active")
    list_filter = ("day", "is_virtual", "is_active")
    list_editable = ("is_active",)


@admin.register(TeachingPhilosophy)
class TeachingPhilosophyAdmin(admin.ModelAdmin):
    list_display = ("headline", "is_active", "updated_at")
    list_editable = ("is_active",)


@admin.register(StudentAnnouncement)
class StudentAnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "is_urgent", "created_at")
    list_filter = ("status", "is_urgent")
    list_editable = ("is_urgent",)
    actions = ["mark_published", "mark_archived"]

    @admin.action(description="✅ Mark selected as Published")
    def mark_published(self, request, queryset):
        save_queryset_with_history(
            queryset,
            request,
            status=StudentAnnouncement.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    @admin.action(description="📦 Mark selected as Archived")
    def mark_archived(self, request, queryset):
        save_queryset_with_history(queryset, request, status="archived")
