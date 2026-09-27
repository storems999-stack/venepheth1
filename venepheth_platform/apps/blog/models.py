"""
Blog / Articles models with versioning and publish workflow.
"""
import bleach
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import PublishableModel, SlugModel, SEOModel
from apps.core.file_security import validate_file_extension, validate_file_size, validate_file_mime

ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "s", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "code", "pre", "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
    "figure", "figcaption", "hr",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "width", "height", "loading"],
    "blockquote": ["cite"],
    "code": ["class"],
    "pre": ["class"],
    "th": ["scope"],
    "td": ["colspan", "rowspan"],
}


class ArticleTag(models.Model):
    """Tag for categorizing articles."""
    name = models.CharField(_("tag"), max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Article(PublishableModel, SlugModel, SEOModel):
    """A blog article / academic writing."""

    class Category(models.TextChoices):
        ARTICLE = "article", _("Article")
        ANNOUNCEMENT = "announcement", _("Announcement")
        ACADEMIC = "academic", _("Academic Writing")
        NEWS = "news", _("News")
        TUTORIAL = "tutorial", _("Tutorial")

    title = models.CharField(_("title"), max_length=400)
    subtitle = models.CharField(_("subtitle"), max_length=400, blank=True)
    excerpt = models.TextField(_("excerpt"), max_length=500, blank=True)
    content_raw = models.TextField(
        _("content (raw)"),
        help_text=_("Raw HTML from editor. Will be sanitized on save."),
    )
    content = models.TextField(
        _("content (sanitized)"),
        editable=False,
        help_text=_("Auto-sanitized HTML."),
    )
    category = models.CharField(
        _("category"), max_length=30, choices=Category.choices, default=Category.ARTICLE, db_index=True
    )
    tags = models.ManyToManyField(ArticleTag, blank=True, related_name="articles")
    thumbnail = models.ImageField(
        _("thumbnail"), upload_to="blog/thumbnails/", null=True, blank=True,
        validators=[validate_file_extension, validate_file_size, validate_file_mime],
    )
    reading_time = models.PositiveSmallIntegerField(
        _("reading time (min)"), null=True, blank=True, editable=False
    )
    view_count = models.PositiveIntegerField(_("views"), default=0, editable=False)
    is_featured = models.BooleanField(_("featured"), default=False)
    allow_comments = models.BooleanField(_("allow comments"), default=False)

    class Meta:
        verbose_name = _("article")
        verbose_name_plural = _("articles")
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["status", "is_featured"]),
        ]

    def __str__(self):
        return self.title
        
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("blog:detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        """Sanitize HTML content and estimate reading time before saving."""
        # Sanitize
        self.content = bleach.clean(
            self.content_raw,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True,
        )
        # Estimate reading time (200 words/min average)
        word_count = len(bleach.clean(self.content, tags=[], strip=True).split())
        self.reading_time = max(1, word_count // 200)
        super().save(*args, **kwargs)
