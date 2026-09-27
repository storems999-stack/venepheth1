from django.db import migrations


def create_backup_schedule(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period="days",
    )

    PeriodicTask.objects.get_or_create(
        name="Daily Platform Backup",
        defaults={
            "task": "apps.core.tasks.daily_backup",
            "interval": schedule,
            "enabled": True,
            "description": "Daily 3-2-1 platform backup",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_backup_schedule, migrations.RunPython.noop),
    ]
