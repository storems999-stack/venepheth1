"""
Notifications model.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    """In-app notification for users."""

    class Level(models.TextChoices):
        INFO = "info", _("Info")
        SUCCESS = "success", _("Success")
        WARNING = "warning", _("Warning")
        ERROR = "error", _("Error")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    message = models.CharField(_("message"), max_length=500)
    link = models.URLField(_("link"), blank=True)
    is_read = models.BooleanField(_("read"), default=False)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.message[:50]}"
