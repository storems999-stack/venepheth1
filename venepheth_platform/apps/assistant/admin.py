from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "language", "is_active", "has_file", "updated_at")
    list_filter = ("is_active", "language")
    search_fields = ("title", "summary", "content", "tags")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_active",)
    fieldsets = (
        (None, {"fields": ("title", "slug", "summary", "language", "is_active")}),
        (_("Knowledge content (AI reads this)"), {"fields": ("content", "tags", "source_url")}),
        (_("Optional file"), {"fields": ("file", "extracted_preview")}),
    )
    readonly_fields = ("extracted_preview",)
    actions = ("reindex_files",)

    @admin.display(boolean=True, description=_("file"))
    def has_file(self, obj):
        return bool(obj.file)

    @admin.display(description=_("Extracted file text (what the AI indexes)"))
    def extracted_preview(self, obj):
        from django.utils.html import escape, format_html

        if not obj.file:
            return _("No file attached — the AI uses the text above.")
        text = (obj.file_text or "").strip()
        if not text:
            return format_html(
                "<span style='color:#b45309;'>{}</span>",
                _("No text extracted yet. Save again or run: python manage.py reindex_knowledge"),
            )
        preview = escape(text[:800]) + ("…" if len(text) > 800 else "")
        return format_html(
            "<p>{}: <strong>{}</strong></p><pre style='white-space:pre-wrap;max-height:220px;overflow:auto;'>"
            "{}</pre>",
            _("Indexed characters"),
            len(text),
            preview,
        )

    @admin.action(description=_("Re-extract text from attached files"))
    def reindex_files(self, request, queryset):
        done, skipped = 0, 0
        for doc in queryset:
            try:
                extracted = doc.extract_file_text()
                if extracted is None:
                    skipped += 1
                    continue
                doc.file_text = extracted
                doc.save(update_fields=["file_text", "updated_at"])
                done += 1
            except Exception:
                skipped += 1
        self.message_user(request, _("Re-indexed %(done)d document(s), skipped %(skipped)d.") % {"done": done, "skipped": skipped})
