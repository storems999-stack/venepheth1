from django.contrib import admin
from .models import ResourceCategory, Resource

@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'icon')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'resource_type', 'visibility', 'is_featured', 'download_count')
    list_filter = ('resource_type', 'visibility', 'is_featured', 'category')
    search_fields = ('title', 'description', 'author', 'tags')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('file_size', 'file_hash', 'download_count', 'view_count')
    fieldsets = (
        ('Core', {
            'fields': ('title', 'slug', 'category', 'resource_type', 'description')
        }),
        ('File / Link', {
            'fields': ('file', 'external_url', 'file_size', 'file_hash')
        }),
        ('Metadata', {
            'fields': ('author', 'year', 'tags', 'version', 'language')
        }),
        ('Access Control & Stats', {
            'fields': ('visibility', 'related_course', 'is_featured', 'download_count', 'view_count')
        })
    )
