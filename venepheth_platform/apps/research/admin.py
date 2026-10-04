from django.contrib import admin

from apps.core.admin_actions import save_queryset_with_history

from .models import Publication, ResearchProject, ResearchTopic


@admin.register(ResearchTopic)
class ResearchTopicAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.action(description="Publish selected items")
def make_published(modeladmin, request, queryset):
    from django.utils import timezone

    count = save_queryset_with_history(queryset, request, status="published", published_at=timezone.now())
    modeladmin.message_user(request, f"{count} item(s) successfully marked as published.")


@admin.action(description="Archive selected items")
def make_archived(modeladmin, request, queryset):
    count = save_queryset_with_history(queryset, request, status="archived")
    modeladmin.message_user(request, f"{count} item(s) successfully archived.")


@admin.register(ResearchProject)
class ResearchProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "research_status", "status", "start_date", "featured")
    list_filter = ("research_status", "status", "featured")
    search_fields = ("title", "abstract", "funding_source")
    actions = [make_published, make_archived]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("topics",)
    date_hierarchy = "start_date"

    class Media:
        js = (
            "https://cdn.tiny.cloud/1/no-api-key/tinymce/6/tinymce.min.js",
            "js/admin_tinymce.js",
        )


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("title", "publication_type", "year", "authors", "status", "featured")
    list_filter = ("publication_type", "status", "featured", "year")
    search_fields = ("title", "abstract", "authors", "doi")
    actions = [make_published, make_archived]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("topics", "related_projects")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ("cited_by",)
        return self.readonly_fields
