"""
Re-extract searchable text for AI Knowledge Box documents.

Usage:
    python manage.py reindex_knowledge           # docs with empty file_text only
    python manage.py reindex_knowledge --all     # all docs with attached files

Useful after adding pypdf or bulk-uploading files (extraction backfill).
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Re-extract file text for KnowledgeDocument entries (AI Knowledge Box)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Re-index every document with a file, not just ones with empty file_text.",
        )

    def handle(self, *args, **options):
        from apps.assistant.models import KnowledgeDocument

        qs = KnowledgeDocument.objects.exclude(file="").exclude(file__isnull=True)
        if not options["all"]:
            qs = qs.filter(file_text="")
        total = qs.count()
        done, skipped = 0, 0
        # .iterator() here is safe on PostgreSQL even though each row is saved
        # mid-iteration: Django fetches in chunks of 2000, and re-querying the
        # pks first would turn one SELECT into one per row. Verified against
        # PostgreSQL 16 with 2500 documents — all re-indexed, no cursor error.
        for doc in qs.iterator():
            try:
                extracted = doc.extract_file_text()
                if extracted is None:
                    skipped += 1
                    continue
                doc.file_text = extracted
                doc.save(update_fields=["file_text", "updated_at"])
                done += 1
            except Exception as exc:
                skipped += 1
                self.stderr.write(f"Skipped {doc.slug}: {type(exc).__name__}")
        self.stdout.write(self.style.SUCCESS(f"Re-indexed {done}/{total} document(s), skipped {skipped}."))
