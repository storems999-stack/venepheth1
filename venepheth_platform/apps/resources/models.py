"""
Digital Resource Library models.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.file_security import (
    secure_upload_path,
    validate_file_extension,
    validate_file_mime,
    validate_file_size,
)
from apps.core.models import SlugModel, TimeStampedModel


class ResourceCategory(TimeStampedModel):
    """Category for organizing digital resources."""

    name = models.CharField(_("name"), max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(_("icon name"), max_length=50, blank=True, help_text=_("Lucide icon name"))
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("resource category")
        verbose_name_plural = _("resource categories")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


def resource_file_path(instance, filename):
    return secure_upload_path(instance, filename, subdir="resources/files")


class Resource(TimeStampedModel, SlugModel):
    """A digital resource in the library."""

    class ResourceType(models.TextChoices):
        LECTURE_NOTE = "lecture_note", _("Lecture Notes")
        PDF = "pdf", _("PDF Document")
        BOOK = "book", _("Book")
        SLIDES = "slides", _("Presentation Slides")
        ASSIGNMENT = "assignment", _("Assignment / Exercise")
        TEMPLATE = "template", _("Template")
        DATASET = "dataset", _("Research Data / Dataset")
        VIDEO = "video", _("Video")
        EXTERNAL = "external", _("External Link")
        OTHER = "other", _("Other")

    class Visibility(models.TextChoices):
        PUBLIC = "public", _("Public — anyone can access")
        STUDENTS = "students", _("Students Only")
        PRIVATE = "private", _("Private — admin only")

    # ─── Core Fields ─────────────────────────────────────────────────────────
    title = models.CharField(_("title"), max_length=300)
    description = models.TextField(_("description"), blank=True)
    category = models.ForeignKey(
        ResourceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="resources"
    )
    resource_type = models.CharField(
        _("type"), max_length=30, choices=ResourceType.choices, default=ResourceType.OTHER, db_index=True
    )

    # ─── Author / Metadata ───────────────────────────────────────────────────
    author = models.CharField(_("author"), max_length=300, blank=True)
    year = models.PositiveSmallIntegerField(_("year"), null=True, blank=True)
    tags = models.CharField(_("tags"), max_length=500, blank=True, help_text=_("Comma-separated tags"))
    version = models.CharField(_("version"), max_length=20, blank=True, default="1.0")
    language = models.CharField(_("language"), max_length=50, default="Lao")

    # ─── File / Link ─────────────────────────────────────────────────────────
    file = models.FileField(
        _("file"),
        upload_to=resource_file_path,
        null=True,
        blank=True,
        validators=[validate_file_extension, validate_file_size, validate_file_mime],
    )
    file_size = models.PositiveBigIntegerField(_("file size (bytes)"), null=True, blank=True, editable=False)
    file_hash = models.CharField(_("file SHA-256"), max_length=64, blank=True, editable=False)
    external_url = models.URLField(_("external URL"), blank=True)

    # ─── Access Control ───────────────────────────────────────────────────────
    visibility = models.CharField(
        _("visibility"), max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC, db_index=True
    )
    related_course = models.ForeignKey(
        "courses.Course", on_delete=models.SET_NULL, null=True, blank=True, related_name="library_resources"
    )

    # ─── Stats ───────────────────────────────────────────────────────────────
    download_count = models.PositiveIntegerField(_("downloads"), default=0, editable=False)
    view_count = models.PositiveIntegerField(_("views"), default=0, editable=False)
    is_featured = models.BooleanField(_("featured"), default=False)

    class Meta:
        verbose_name = _("resource")
        verbose_name_plural = _("resources")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["resource_type", "visibility"]),
            models.Index(fields=["visibility", "is_featured"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("resources:detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        """Auto-compute file size and hash on save."""
        if self.file:
            try:
                from apps.core.file_security import compute_file_hash

                self.file_size = self.file.size
                if not self.file_hash:
                    self.file_hash = compute_file_hash(self.file)
            except Exception:
                pass
        super().save(*args, **kwargs)

    def get_tags_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]
