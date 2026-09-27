"""
Tests for Automated Backup and Disaster Recovery (Pillar 1).
"""
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase


class BackupAndDisasterRecoveryTests(TestCase):
    """Verifies automated 3-2-1 backup creation, checksum, and restore verification."""

    def setUp(self):
        self.test_backup_dir = Path(tempfile.mkdtemp(prefix="test_backup_"))

    def tearDown(self):
        if self.test_backup_dir.exists():
            shutil.rmtree(self.test_backup_dir, ignore_errors=True)

    def test_backup_platform_command_creates_archive_and_checksum(self):
        """Test backup_platform generates .tar.gz and matching .sha256 file."""
        call_command("backup_platform", output_dir=str(self.test_backup_dir), no_media=True)

        archives = list(self.test_backup_dir.glob("backup_venepheth_platform_*.tar.gz"))
        self.assertEqual(len(archives), 1, "Expected exactly 1 backup archive generated")
        archive = archives[0]

        checksum_file = archive.with_name(f"{archive.name}.sha256")
        self.assertTrue(checksum_file.exists(), "Expected .sha256 checksum file to exist")

        with open(checksum_file, "r", encoding="utf-8") as f:
            checksum_content = f.read().strip()
        self.assertIn(archive.name, checksum_content)

    def test_restore_platform_verifies_checksum(self):
        """Test restore_platform detects corrupted archive checksum."""
        call_command("backup_platform", output_dir=str(self.test_backup_dir), no_media=True)
        archive = list(self.test_backup_dir.glob("backup_venepheth_platform_*.tar.gz"))[0]
        checksum_file = archive.with_name(f"{archive.name}.sha256")

        # Tamper with checksum file
        with open(checksum_file, "w", encoding="utf-8") as f:
            f.write(f"badchecksum1234567890  {archive.name}\n")

        from django.core.management.base import CommandError
        with self.assertRaises(CommandError) as ctx:
            call_command("restore_platform", archive=str(archive), confirm=True)
        self.assertIn("Integrity Check Failed", str(ctx.exception))


class CeleryBeatBackupTests(TestCase):
    """Verify scheduled daily backup task and schedule."""

    def test_daily_backup_schedule_exists(self):
        """IntervalSchedule and PeriodicTask for daily backup must exist."""
        from django_celery_beat.models import IntervalSchedule, PeriodicTask

        schedule_exists = IntervalSchedule.objects.filter(
            every=1, period=IntervalSchedule.DAYS
        ).exists()
        self.assertTrue(schedule_exists, "Daily interval schedule missing")

        task_exists = PeriodicTask.objects.filter(
            name="Daily Platform Backup",
            task="apps.core.tasks.daily_backup",
        ).exists()
        self.assertTrue(task_exists, "Daily backup periodic task missing")

    def test_daily_backup_task_calls_backup_command(self):
        """daily_backup Celery task should invoke backup_platform with expected args."""
        from apps.core.tasks import daily_backup

        with patch("apps.core.tasks.call_command") as mock_call:
            daily_backup.apply()

        mock_call.assert_called_once_with(
            "backup_platform",
            output_dir=str(settings.BASE_DIR / "backups"),
            keep_days=14,
            no_media=False,
        )
