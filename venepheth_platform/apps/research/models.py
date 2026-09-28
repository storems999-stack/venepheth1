"""
Research and Publications models.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.file_security import (
    validate_file_extension,
    validate_file_mime,
    validate_file_size,
)
from apps.core.models import PublishableModel, SEOModel, SlugModel, TimeStampedModel


class ResearchTopic(TimeStampedModel):
    """Research interest/topic tag."""

    name = models.CharField(_("name"), max_length=200, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ResearchProject(PublishableModel, SlugModel, SEOModel):
    """A research project."""

    class ResearchStatus(models.TextChoices):
        PROPOSED = "proposed", _("Proposed")
        ONGOING = "ongoing", _("Ongoing")
        COMPLETED = "completed", _("Completed")
        PUBLISHED = "published", _("Published")
        SUSPENDED = "suspended", _("Suspended")

    title = models.CharField(_("title"), max_length=400)
    short_title = models.CharField(_("short title"), max_length=200, blank=True)
    abstract = models.TextField(_("abstract"))
    research_status = models.CharField(
        _("research status"),
        max_length=20,
        choices=ResearchStatus.choices,
        default=ResearchStatus.ONGOING,
        db_index=True,
    )
    topics = models.ManyToManyField(ResearchTopic, blank=True, related_name="projects")
    funding_source = models.CharField(_("funding source"), max_length=300, blank=True)
    start_date = models.DateField(_("start date"), null=True, blank=True)
    end_date = models.DateField(_("end date"), null=True, blank=True)
    collaborators = models.TextField(_("collaborators"), blank=True)
    external_url = models.URLField(_("external URL"), blank=True)
    featured = models.BooleanField(_("featured"), default=False)

    class Meta:
        verbose_name = _("research project")
        ordering = ["-start_date", "-created_at"]
        indexes = [
            models.Index(fields=["status", "research_status"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("research:project_detail", kwargs={"slug": self.slug})


class Publication(PublishableModel, SlugModel, SEOModel):
    """A scholarly publication."""

    class PublicationType(models.TextChoices):
        JOURNAL = "journal", _("Journal Article")
        CONFERENCE = "conference", _("Conference Paper")
        BOOK = "book", _("Book")
        BOOK_CHAPTER = "book_chapter", _("Book Chapter")
        THESIS = "thesis", _("Thesis / Dissertation")
        WORKING_PAPER = "working_paper", _("Working Paper")
        REPORT = "report", _("Report")
        OTHER = "other", _("Other")

    title = models.CharField(_("title"), max_length=500)
    publication_type = models.CharField(_("type"), max_length=30, choices=PublicationType.choices, db_index=True)
    abstract = models.TextField(_("abstract"), blank=True)
    authors = models.CharField(_("authors"), max_length=500, help_text=_("Comma-separated list of authors"))
    year = models.PositiveSmallIntegerField(_("year"), null=True, blank=True, db_index=True)
    journal_name = models.CharField(_("journal / venue"), max_length=300, blank=True)
    volume = models.CharField(_("volume"), max_length=50, blank=True)
    issue = models.CharField(_("issue"), max_length=50, blank=True)
    pages = models.CharField(_("pages"), max_length=50, blank=True)
    doi = models.CharField(_("DOI"), max_length=200, blank=True, db_index=True)
    isbn = models.CharField(_("ISBN"), max_length=50, blank=True)
    keywords = models.CharField(_("keywords"), max_length=500, blank=True)
    external_url = models.URLField(_("URL"), blank=True)
    pdf_file = models.FileField(
        _("PDF"),
        upload_to="publications/pdfs/",
        null=True,
        blank=True,
        validators=[validate_file_extension, validate_file_size, validate_file_mime],
    )
    cited_by = models.PositiveIntegerField(_("times cited"), default=0)
    topics = models.ManyToManyField(ResearchTopic, blank=True, related_name="publications")
    related_projects = models.ManyToManyField(ResearchProject, blank=True, related_name="publications")
    featured = models.BooleanField(_("featured"), default=False)

    class Meta:
        verbose_name = _("publication")
        ordering = ["-year", "-created_at"]
        indexes = [
            models.Index(fields=["publication_type", "year"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.year})"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("publications:detail", kwargs={"slug": self.slug})

    @property
    def doi_url(self):
        """Resolves to a full https:// URL regardless of stored DOI format."""
        if not self.doi:
            return ""
        doi = self.doi.strip()
        if doi.startswith(("http://", "https://")):
            return doi
        if doi.lower().startswith("doi:"):
            doi = doi[4:]
        return f"https://doi.org/{doi}"

    @property
    def citation_apa(self):
        """Generate a simple APA-style citation."""
        parts = [self.authors]
        if self.year:
            parts.append(f"({self.year}).")
        parts.append(f"{self.title}.")
        if self.journal_name:
            parts.append(f"*{self.journal_name}*")
        if self.volume:
            parts.append(f", {self.volume}")
        if self.issue:
            parts.append(f"({self.issue})")
        if self.pages:
            parts.append(f", {self.pages}.")
        if self.doi_url:
            parts.append(f" {self.doi_url}")
        return " ".join(parts)
