"""
Academic Events models.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.file_security import (
    validate_file_extension,
    validate_file_mime,
    validate_file_size,
)
from apps.core.models import PublishableModel, SEOModel, SlugModel


class Event(PublishableModel, SlugModel, SEOModel):
    """Academic event, seminar, or workshop."""

    class EventType(models.TextChoices):
        SEMINAR = "seminar", _("Seminar")
        WORKSHOP = "workshop", _("Workshop")
        CONFERENCE = "conference", _("Conference")
        GUEST_LECTURE = "guest_lecture", _("Guest Lecture")
        WEBINAR = "webinar", _("Webinar")
        OTHER = "other", _("Other")

    title = models.CharField(_("title"), max_length=400)
    event_type = models.CharField(
        _("type"), max_length=30, choices=EventType.choices, default=EventType.SEMINAR, db_index=True
    )
    description = models.TextField(_("description"))
    location = models.CharField(_("location"), max_length=400, blank=True)
    is_virtual = models.BooleanField(_("is virtual"), default=False)
    registration_link = models.URLField(_("registration link"), blank=True)
    start_time = models.DateTimeField(_("start time"), db_index=True)
    end_time = models.DateTimeField(_("end time"), null=True, blank=True)
    cover_image = models.ImageField(
        _("cover image"),
        upload_to="events/covers/",
        null=True,
        blank=True,
        validators=[validate_file_extension, validate_file_size, validate_file_mime],
    )
    organizer = models.CharField(_("organizer"), max_length=300, blank=True)

    class Meta:
        verbose_name = _("event")
        verbose_name_plural = _("events")
        ordering = ["-start_time", "-created_at"]
        indexes = [
            models.Index(fields=["status", "start_time"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_time:%Y-%m-%d})"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("events:detail", kwargs={"slug": self.slug})
