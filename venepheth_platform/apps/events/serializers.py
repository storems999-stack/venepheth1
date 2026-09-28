from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "event_type",
            "event_type_display",
            "description",
            "location",
            "is_virtual",
            "registration_link",
            "start_time",
            "end_time",
            "cover_image",
            "organizer",
            "published_at",
        ]
