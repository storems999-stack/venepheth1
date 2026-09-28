from django.contrib import admin

from .models import Article, ArticleTag


@admin.register(ArticleTag)
class ArticleTagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.action(description="Publish selected articles")
def make_published(modeladmin, request, queryset):
    from django.utils import timezone

    count = queryset.update(status=Article.Status.PUBLISHED, published_at=timezone.now())
    modeladmin.message_user(request, f"{count} article(s) successfully marked as published.")


@admin.action(description="Archive selected articles")
def make_archived(modeladmin, request, queryset):
    count = queryset.update(status=Article.Status.ARCHIVED)
    modeladmin.message_user(request, f"{count} article(s) successfully archived.")


@admin.action(description="Revert selected articles to draft")
def make_draft(modeladmin, request, queryset):
    count = queryset.update(status=Article.Status.DRAFT)
    modeladmin.message_user(request, f"{count} article(s) reverted to draft.")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "published_at", "is_featured", "view_count")
    list_filter = ("status", "category", "is_featured")
    search_fields = ("title", "subtitle", "content_raw")
    actions = [make_published, make_archived, make_draft]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags",)
    readonly_fields = ("content", "reading_time", "view_count")
    fieldsets = (
        (
            "Article Content",
            {"fields": ("title", "slug", "subtitle", "category", "excerpt", "content_raw", "content", "thumbnail")},
        ),
        ("Publication", {"fields": ("status", "published_at", "is_featured", "tags", "allow_comments")}),
        ("Stats (Auto)", {"fields": ("reading_time", "view_count")}),
        ("SEO", {"fields": ("seo_title", "seo_description", "og_image"), "classes": ("collapse",)}),
    )

    class Media:
        js = (
            "https://cdn.tiny.cloud/1/no-api-key/tinymce/6/tinymce.min.js",
            "js/admin_tinymce.js",
        )
