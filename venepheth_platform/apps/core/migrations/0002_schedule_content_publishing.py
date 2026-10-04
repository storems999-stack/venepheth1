from django.db import migrations


def create_scheduled_publishing_task(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period="minutes",
    )
    PeriodicTask.objects.get_or_create(
        name="Publish Scheduled Content",
        defaults={
            "task": "apps.core.tasks.publish_scheduled_content",
            "interval": schedule,
            "enabled": True,
            "description": "Publish scheduled content when its release time arrives",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_create_backup_schedule"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_scheduled_publishing_task, migrations.RunPython.noop),
    ]
