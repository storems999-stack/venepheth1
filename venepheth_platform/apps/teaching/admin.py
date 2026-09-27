"""Teaching app admin."""
from django.contrib import admin
from .models import OfficeHours, TeachingPhilosophy, StudentAnnouncement


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
    list_editable = ("status",)
    actions = ["mark_published", "mark_archived"]

    @admin.action(description="✅ Mark selected as Published")
    def mark_published(self, request, queryset):
        queryset.update(status="published")

    @admin.action(description="📦 Mark selected as Archived")
    def mark_archived(self, request, queryset):
        queryset.update(status="archived")
