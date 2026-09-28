"""
Analytics models.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PageView(models.Model):
    """Privacy-respecting page view tracker."""

    path = models.CharField(_("path"), max_length=255, db_index=True)
    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True)
    referer = models.URLField(_("referer"), max_length=512, blank=True)
    is_authenticated = models.BooleanField(_("authenticated"), default=False)

    class Meta:
        verbose_name = _("page view")
        verbose_name_plural = _("page views")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["path", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.path} at {self.timestamp}"
