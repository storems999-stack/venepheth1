from django.urls import reverse
from rest_framework import serializers

from .models import Publication, ResearchProject, ResearchTopic


class ResearchTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchTopic
        fields = ["id", "name", "slug"]


class ResearchProjectSerializer(serializers.ModelSerializer):
    topics = ResearchTopicSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_research_status_display", read_only=True)

    class Meta:
        model = ResearchProject
        fields = [
            "id",
            "title",
            "slug",
            "abstract",
            "research_status",
            "status_display",
            "start_date",
            "end_date",
            "funding_source",
            "featured",
            "published_at",
            "topics",
        ]


class PublicationSerializer(serializers.ModelSerializer):
    topics = ResearchTopicSerializer(many=True, read_only=True)
    type_display = serializers.CharField(source="get_publication_type_display", read_only=True)
    pdf_file = serializers.SerializerMethodField()

    def get_pdf_file(self, obj: Publication) -> str | None:
        if not obj.pdf_file:
            return None
        path = reverse("publications:download", kwargs={"slug": obj.slug})
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path

    class Meta:
        model = Publication
        fields = [
            "id",
            "title",
            "slug",
            "publication_type",
            "type_display",
            "abstract",
            "authors",
            "year",
            "journal_name",
            "volume",
            "issue",
            "pages",
            "doi",
            "isbn",
            "keywords",
            "cited_by",
            "featured",
            "pdf_file",
            "external_url",
            "published_at",
            "topics",
        ]
