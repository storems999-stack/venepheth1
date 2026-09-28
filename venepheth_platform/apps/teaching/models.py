"""
Teaching app models — office hours, student announcements, advising.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import PublishableModel, TimeStampedModel


class OfficeHours(TimeStampedModel):
    """Weekly office hours schedule."""

    class Day(models.TextChoices):
        MON = "monday", _("Monday")
        TUE = "tuesday", _("Tuesday")
        WED = "wednesday", _("Wednesday")
        THU = "thursday", _("Thursday")
        FRI = "friday", _("Friday")
        SAT = "saturday", _("Saturday")

    day = models.CharField(_("day"), max_length=20, choices=Day.choices)
    start_time = models.TimeField(_("start time"))
    end_time = models.TimeField(_("end time"))
    location = models.CharField(_("location / room"), max_length=200, blank=True)
    is_virtual = models.BooleanField(_("virtual / online"), default=False)
    meeting_link = models.URLField(_("meeting link"), blank=True)
    notes = models.CharField(_("notes"), max_length=300, blank=True)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("office hours")
        verbose_name_plural = _("office hours")
        ordering = ["day", "start_time"]

    def __str__(self):
        return f"{self.get_day_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"


class TeachingPhilosophy(TimeStampedModel):
    """Teaching philosophy statement (singleton)."""

    headline = models.CharField(_("headline"), max_length=200)
    body = models.TextField(_("statement"))
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("teaching philosophy")
        verbose_name_plural = _("teaching philosophies")

    def __str__(self):
        return self.headline


class StudentAnnouncement(PublishableModel):
    """Short announcements directed at students."""

    title = models.CharField(_("title"), max_length=300)
    body = models.TextField(_("body"))
    is_urgent = models.BooleanField(_("urgent"), default=False)

    class Meta:
        verbose_name = _("student announcement")
        verbose_name_plural = _("student announcements")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
