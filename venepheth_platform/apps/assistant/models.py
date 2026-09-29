"""
Knowledge Box for AI Academic Assistant (RAG).

Admins upload/paste documents here — the AcademicRetriever searches them
first (highest priority) before falling back to courses/research/etc.
Zero-cost: plain keyword search, no vector DB required.
"""

import logging

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.file_security import (
    secure_upload_path,
    validate_file_extension,
    validate_file_mime,
    validate_file_size,
)

logger = logging.getLogger("apps.assistant")


def knowledge_file_path(instance, filename):
    return secure_upload_path(instance, filename, subdir="assistant/knowledge")


# Caps to keep save() fast and DB rows small.
MAX_EXTRACT_BYTES = 200_000
MAX_EXTRACT_CHARS = 20_000
MAX_PDF_PAGES = 20


def extract_pdf_text(file_obj, max_pages: int = MAX_PDF_PAGES, max_chars: int = MAX_EXTRACT_CHARS) -> str:
    """Extract text from a PDF file object. Returns '' on any failure.

    Zero-cost + dependency-light: uses pypdf when installed, otherwise
    returns '' so save() never breaks (admin can paste text manually).
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("KnowledgeDocument: pypdf not installed; skipping PDF extraction")
        return ""
    try:
        file_obj.seek(0)
        reader = PdfReader(file_obj)
        chunks: list[str] = []
        total = 0
        for page in reader.pages[:max_pages]:
            try:
                text = page.extract_text() or ""
            except Exception:
                continue
            if text:
                chunks.append(text)
                total += len(text)
                if total >= max_chars:
                    break
        return "\n".join(chunks)[:max_chars]
    except Exception:
        logger.warning("KnowledgeDocument: PDF extraction failed", exc_info=True)
        return ""
    finally:
        try:
            file_obj.seek(0)
        except Exception:
            pass


class KnowledgeDocument(models.Model):
    """A curated knowledge entry the AI can cite."""

    title = models.CharField(_("title"), max_length=300)
    slug = models.SlugField(unique=True, blank=True, max_length=320)
    summary = models.CharField(_("summary"), max_length=500, blank=True)
    content = models.TextField(
        _("knowledge text"),
        blank=True,
        help_text=_("Paste FAQ / policy / course info here. Searched by the AI."),
    )
    file = models.FileField(
        _("supporting file (txt/md/pdf)"),
        upload_to=knowledge_file_path,
        null=True,
        blank=True,
        validators=[validate_file_extension, validate_file_size, validate_file_mime],
        help_text=_("Optional. .txt/.md/.pdf text is auto-indexed for the AI."),
    )
    file_text = models.TextField(_("extracted file text"), blank=True, editable=False)
    tags = models.CharField(_("tags"), max_length=500, blank=True, help_text=_("Comma-separated tags"))
    language = models.CharField(_("language"), max_length=10, default="en", choices=[("en", "English"), ("lo", "ລາວ")])
    source_url = models.URLField(_("source link"), blank=True)
    is_active = models.BooleanField(_("active (visible to AI)"), default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("knowledge document")
        verbose_name_plural = _("knowledge documents (AI Knowledge Box)")
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """Link to the source page, or the assistant as a fallback."""
        from django.urls import reverse

        url = (self.source_url or "").strip()
        if url.startswith("/") or url.startswith("https://") or url.startswith("http://"):
            return url
        return reverse("assistant:chat")

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True)[:300] or "doc"
            slug, i = base, 1
            while KnowledgeDocument.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        # Auto-extract uploads so RAG can search them.
        if self.file:
            try:
                extracted = self.extract_file_text()
                if extracted is not None:
                    self.file_text = extracted
                # None = unsupported type: keep existing file_text.
            except Exception:
                logger.warning("KnowledgeDocument: failed to extract text for %r", self.title)
        super().save(*args, **kwargs)

    def extract_file_text(self) -> str | None:
        """(Re-)extract searchable text from the attached file.

        Returns the extracted text, '' when extraction yields nothing, or
        None for unsupported file types (existing file_text is kept then).
        """
        if not self.file:
            return ""
        name = (self.file.name or "").lower()
        if name.endswith((".txt", ".md", ".markdown")):
            self.file.seek(0)
            raw = self.file.read(MAX_EXTRACT_BYTES)
            self.file.seek(0)
            return raw.decode("utf-8", errors="ignore")[:MAX_EXTRACT_CHARS]
        if name.endswith(".pdf"):
            return extract_pdf_text(self.file)
        return None

    def searchable_text(self) -> str:
        parts = [self.title, self.summary, self.content, self.file_text, self.tags]
        return "\n".join(p for p in parts if p)
