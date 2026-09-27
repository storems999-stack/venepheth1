"""
Contact form model with rate limiting.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class ContactMessage(TimeStampedModel):
    """Message submitted through the contact form."""

    class Status(models.TextChoices):
        NEW = "new", _("New")
        READ = "read", _("Read")
        REPLIED = "replied", _("Replied")
        SPAM = "spam", _("Spam")
        ARCHIVED = "archived", _("Archived")

    name = models.CharField(_("name"), max_length=200)
    email = models.EmailField(_("email"))
    subject = models.CharField(_("subject"), max_length=300)
    message = models.TextField(_("message"), max_length=5000)
    organization = models.CharField(_("organization"), max_length=200, blank=True)
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True)
    replied_at = models.DateTimeField(_("replied at"), null=True, blank=True)
    notes = models.TextField(_("internal notes"), blank=True)

    class Meta:
        verbose_name = _("contact message")
        verbose_name_plural = _("contact messages")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject}"
