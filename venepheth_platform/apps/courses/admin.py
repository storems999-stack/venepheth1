from django.contrib import admin

from .models import (
    Announcement,
    Course,
    CourseCategory,
    CourseModule,
    CourseResource,
    LearningOutcome,
)


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    prepopulated_fields = {"slug": ("name",)}


class LearningOutcomeInline(admin.TabularInline):
    model = LearningOutcome
    extra = 1


class CourseModuleInline(admin.StackedInline):
    model = CourseModule
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "status", "featured", "visibility")
    list_filter = ("status", "featured", "visibility", "category")
    search_fields = ("code", "name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [LearningOutcomeInline, CourseModuleInline]
    fieldsets = (
        ("Core Information", {"fields": ("code", "name", "slug", "category", "description", "short_description")}),
        ("Academic Details", {"fields": ("credits", "semester", "academic_year", "level", "language")}),
        ("Display & Access", {"fields": ("thumbnail", "featured", "visibility", "status", "published_at")}),
        ("SEO", {"fields": ("seo_title", "seo_description", "og_image"), "classes": ("collapse",)}),
    )

    class Media:
        js = (
            "https://cdn.tiny.cloud/1/no-api-key/tinymce/6/tinymce.min.js",
            "js/admin_tinymce.js",
        )


@admin.register(CourseResource)
class CourseResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "module", "resource_type", "visibility")
    list_filter = ("resource_type", "visibility", "course")
    search_fields = ("title", "description")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "status", "is_pinned")
    list_filter = ("status", "is_pinned", "course")
    search_fields = ("title", "content")
