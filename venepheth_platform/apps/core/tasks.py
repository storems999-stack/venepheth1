"""Core Celery tasks."""
from celery import shared_task
from django.conf import settings
from django.core.management import call_command


@shared_task(bind=True, ignore_result=True)
def daily_backup(self):
    """Run the daily 3-2-1 platform backup."""
    call_command(
        "backup_platform",
        output_dir=str(settings.BASE_DIR / "backups"),
        keep_days=14,
        no_media=False,
    )
