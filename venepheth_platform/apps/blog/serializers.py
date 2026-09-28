from rest_framework import serializers

from .models import Article, ArticleTag


class ArticleTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleTag
        fields = ["id", "name", "slug"]


class ArticleListSerializer(serializers.ModelSerializer):
    tags = ArticleTagSerializer(many=True, read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "subtitle",
            "slug",
            "excerpt",
            "category",
            "category_display",
            "is_featured",
            "published_at",
            "thumbnail",
            "reading_time",
            "view_count",
            "tags",
        ]


class ArticleDetailSerializer(serializers.ModelSerializer):
    tags = ArticleTagSerializer(many=True, read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "subtitle",
            "slug",
            "excerpt",
            "content_raw",
            "category",
            "category_display",
            "is_featured",
            "published_at",
            "thumbnail",
            "reading_time",
            "view_count",
            "allow_comments",
            "seo_title",
            "seo_description",
            "tags",
        ]
