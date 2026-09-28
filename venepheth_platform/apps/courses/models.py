"""
Course management models.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.file_security import (
    secure_upload_path,
    validate_file_extension,
    validate_file_mime,
    validate_file_size,
)
from apps.core.models import PublishableModel, SEOModel, SlugModel, TimeStampedModel


class CourseCategory(TimeStampedModel):
    """Category for organizing courses."""

    name = models.CharField(_("name"), max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("course category")
        verbose_name_plural = _("course categories")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Course(PublishableModel, SlugModel, SEOModel):
    """A course taught by the lecturer."""

    class Visibility(models.TextChoices):
        PUBLIC = "public", _("Public")
        ENROLLED = "enrolled", _("Enrolled Students Only")
        PRIVATE = "private", _("Private")

    # ─── Core Info ──────────────────────────────────────────────────────────────
    code = models.CharField(_("course code"), max_length=20, blank=True, db_index=True)
    name = models.CharField(_("course name"), max_length=300)
    description = models.TextField(_("description"))
    short_description = models.CharField(_("short description"), max_length=500, blank=True)
    category = models.ForeignKey(
        CourseCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="courses"
    )

    # ─── Academic Info ──────────────────────────────────────────────────────────
    credits = models.PositiveSmallIntegerField(_("credits"), default=3)
    semester = models.CharField(_("semester"), max_length=50, blank=True)
    academic_year = models.CharField(_("academic year"), max_length=20, blank=True)
    level = models.CharField(_("level"), max_length=50, blank=True, help_text=_("e.g. Undergraduate, Graduate, PhD"))
    language = models.CharField(_("language of instruction"), max_length=50, default="Lao")

    # ─── Display ────────────────────────────────────────────────────────────────
    thumbnail = models.ImageField(
        _("thumbnail"),
        upload_to="courses/thumbnails/",
        null=True,
        blank=True,
        validators=[validate_file_extension, validate_file_size, validate_file_mime],
    )
    featured = models.BooleanField(_("featured"), default=False)
    visibility = models.CharField(_("visibility"), max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)

    class Meta:
        verbose_name = _("course")
        verbose_name_plural = _("courses")
        ordering = ["-academic_year", "-created_at"]
        indexes = [
            models.Index(fields=["status", "featured"]),
            models.Index(fields=["status", "visibility"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}" if self.code else self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("courses:detail", kwargs={"slug": self.slug})


class LearningOutcome(TimeStampedModel):
    """Learning outcomes for a course."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="outcomes")
    description = models.CharField(_("outcome"), max_length=500)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.description[:80]


class CourseModule(TimeStampedModel):
    """A module/week within a course."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(_("title"), max_length=300)
    description = models.TextField(_("description"), blank=True)
    week_number = models.PositiveSmallIntegerField(_("week number"), null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(_("visible to students"), default=True)

    class Meta:
        ordering = ["order", "week_number"]
        verbose_name = _("course module")

    def __str__(self):
        if self.week_number:
            return f"Week {self.week_number:02d}: {self.title}"
        return self.title


def resource_upload_path(instance, filename):
    return secure_upload_path(instance, filename, subdir="courses/resources")


class CourseResource(TimeStampedModel):
    """A resource file or link attached to a course or module."""

    class ResourceType(models.TextChoices):
        PDF = "pdf", _("PDF")
        SLIDES = "slides", _("Slides")
        VIDEO = "video", _("Video")
        LINK = "link", _("External Link")
        DATASET = "dataset", _("Dataset")
        OTHER = "other", _("Other")

    class Visibility(models.TextChoices):
        PUBLIC = "public", _("Public")
        STUDENTS = "students", _("Students Only")
        PRIVATE = "private", _("Private")

    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, null=True, blank=True, related_name="resources")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="resources")
    title = models.CharField(_("title"), max_length=300)
    description = models.TextField(_("description"), blank=True)
    resource_type = models.CharField(_("type"), max_length=20, choices=ResourceType.choices, default=ResourceType.OTHER)
    file = models.FileField(
        _("file"),
        upload_to=resource_upload_path,
        null=True,
        blank=True,
        validators=[validate_file_extension, validate_file_size, validate_file_mime],
    )
    external_url = models.URLField(_("external URL"), blank=True)
    visibility = models.CharField(
        _("visibility"), max_length=20, choices=Visibility.choices, default=Visibility.STUDENTS
    )
    order = models.PositiveSmallIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["order", "created_at"]
        verbose_name = _("course resource")
        indexes = [
            models.Index(fields=["course", "visibility"]),
            models.Index(fields=["module", "visibility"]),
        ]

    def __str__(self):
        return self.title


class Announcement(PublishableModel):
    """Course announcement."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(_("title"), max_length=300)
    content = models.TextField(_("content"))
    is_pinned = models.BooleanField(_("pinned"), default=False)

    class Meta:
        ordering = ["-is_pinned", "-published_at"]

    def __str__(self):
        return self.title
