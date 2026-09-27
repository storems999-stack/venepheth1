from rest_framework import serializers
from .models import Resource, ResourceCategory

class ResourceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceCategory
        fields = ["id", "name", "slug", "icon"]

class ResourceSerializer(serializers.ModelSerializer):
    category = ResourceCategorySerializer(read_only=True)
    resource_type_display = serializers.CharField(source="get_resource_type_display", read_only=True)
    visibility_display = serializers.CharField(source="get_visibility_display", read_only=True)

    class Meta:
        model = Resource
        fields = [
            "id", "title", "slug", "description", "category", "resource_type",
            "resource_type_display", "author", "year", "version", "language",
            "file", "file_size", "external_url", "visibility", "visibility_display",
            "download_count", "view_count", "is_featured", "created_at", "tags"
        ]
