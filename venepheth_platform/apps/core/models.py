"""
Core abstract base models used across all apps.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.file_security import (
    validate_file_extension,
    validate_file_mime,
    validate_file_size,
)


class TimeStampedModel(models.Model):
    """Abstract base model with created_at and updated_at timestamps."""

    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class PublishableModel(TimeStampedModel):
    """Abstract model for content that can be published."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SCHEDULED = "scheduled", _("Scheduled")
        PUBLISHED = "published", _("Published")
        ARCHIVED = "archived", _("Archived")

    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(_("published at"), null=True, blank=True, db_index=True)
    scheduled_at = models.DateTimeField(_("scheduled at"), null=True, blank=True)

    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    def publish(self):
        from django.utils import timezone

        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.save(update_fields=["status", "published_at", "updated_at"])

    def unpublish(self):
        self.status = self.Status.DRAFT
        self.save(update_fields=["status", "updated_at"])

    def archive(self):
        self.status = self.Status.ARCHIVED
        self.save(update_fields=["status", "updated_at"])


class SlugModel(models.Model):
    """Abstract model with a unique slug field."""

    slug = models.SlugField(
        _("slug"),
        max_length=255,
        unique=True,  # unique implies an index — no separate db_index needed
        help_text=_("URL-friendly identifier. Auto-generated from title."),
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Abstract model supporting soft deletion."""

    is_deleted = models.BooleanField(_("deleted"), default=False, db_index=True)
    deleted_at = models.DateTimeField(_("deleted at"), null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class SEOModel(models.Model):
    """Abstract model for SEO metadata fields."""

    seo_title = models.CharField(_("SEO title"), max_length=70, blank=True)
    seo_description = models.CharField(_("SEO description"), max_length=160, blank=True)
    seo_keywords = models.CharField(_("SEO keywords"), max_length=255, blank=True)
    og_image = models.ImageField(
        _("OG image"),
        upload_to="seo/og/",
        null=True,
        blank=True,
        validators=[validate_file_extension, validate_file_size, validate_file_mime],
    )

    class Meta:
        abstract = True

    def get_seo_title(self):
        return self.seo_title or str(self)

    def get_seo_description(self):
        return self.seo_description
