"""Core Celery tasks."""

from celery import shared_task
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone


@shared_task(bind=True, ignore_result=True)
def daily_backup(self):
    """Run the daily 3-2-1 platform backup."""
    call_command(
        "backup_platform",
        output_dir=str(settings.BASE_DIR / "backups"),
        keep_days=14,
        no_media=False,
        encrypt=True,
        upload=True,
    )


@shared_task(ignore_result=True)
def publish_scheduled_content():
    """Publish scheduled content whose release time has arrived."""
    from apps.blog.models import Article
    from apps.courses.models import Announcement, Course
    from apps.research.models import Publication, ResearchProject
    from apps.teaching.models import StudentAnnouncement

    now = timezone.now()
    models = (Article, Course, Announcement, Publication, ResearchProject, StudentAnnouncement)
    published_count = 0
    with transaction.atomic():
        for model in models:
            due_items = model.objects.select_for_update().filter(
                status="scheduled",
                scheduled_at__lte=now,
            )
            for item in due_items.iterator():
                item.status = "published"
                item.published_at = item.scheduled_at
                item.save(update_fields=["status", "published_at", "updated_at"])
                published_count += 1
    return published_count
