"""
Tests for Automated Backup and Disaster Recovery (Pillar 1).
"""

import hashlib
import io
import os
import shutil
import sys
import tarfile
import tempfile
import types
from pathlib import Path
from unittest.mock import Mock, patch

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
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
        archive = next(iter(self.test_backup_dir.glob("backup_venepheth_platform_*.tar.gz")))
        checksum_file = archive.with_name(f"{archive.name}.sha256")

        # Tamper with checksum file
        with open(checksum_file, "w", encoding="utf-8") as f:
            f.write(f"badchecksum1234567890  {archive.name}\n")

        from django.core.management.base import CommandError

        with self.assertRaises(CommandError) as ctx:
            call_command("restore_platform", archive=str(archive), confirm=True)
        self.assertIn("Integrity Check Failed", str(ctx.exception))

    def test_restore_platform_reports_empty_checksum_sidecar(self):
        archive = self.test_backup_dir / "backup_venepheth_platform_empty_checksum.tar.gz"
        archive.write_bytes(b"archive")
        archive.with_name(f"{archive.name}.sha256").write_text("", encoding="utf-8")

        with self.assertRaisesMessage(CommandError, "checksum sidecar is empty"):
            call_command("restore_platform", archive=str(archive), verify_only=True)

    def test_verify_only_rejects_non_archive_with_valid_checksum(self):
        archive = self.test_backup_dir / "backup_venepheth_platform_invalid.tar.gz"
        archive.write_bytes(b"not a tar archive")
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_name(f"{archive.name}.sha256").write_text(
            f"{checksum}  {archive.name}\n",
            encoding="utf-8",
        )

        with self.assertRaisesMessage(CommandError, "contents"):
            call_command("restore_platform", archive=str(archive), verify_only=True)

    def test_verify_only_rejects_invalid_manifest_and_portable_dump(self):
        archive = self.test_backup_dir / "backup_venepheth_platform_invalid_contents.tar.gz"
        members = {
            "manifest.json": b"[]",
            "data_dump.json": b"not json",
        }
        with tarfile.open(archive, "w:gz") as tar:
            for name, content in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_name(f"{archive.name}.sha256").write_text(
            f"{checksum}  {archive.name}\n",
            encoding="utf-8",
        )

        with self.assertRaisesMessage(CommandError, "manifest is invalid"):
            call_command("restore_platform", archive=str(archive), verify_only=True)

    def test_verify_only_accepts_valid_archive_without_restoring_database(self):
        call_command("backup_platform", output_dir=str(self.test_backup_dir), no_media=True)
        archive = next(self.test_backup_dir.glob("backup_venepheth_platform_*.tar.gz"))
        from apps.profiles.models import Profile

        profile_count = Profile.objects.count()

        call_command("restore_platform", archive=str(archive), verify_only=True)

        self.assertEqual(Profile.objects.count(), profile_count)

    def test_encrypted_backup_uploads_archive_and_checksum(self):
        """Off-site upload must include both the encrypted archive and sidecar."""
        key = Fernet.generate_key().decode()
        s3 = Mock()
        boto3 = types.ModuleType("boto3")
        boto3.client = Mock(return_value=s3)
        boto3.__path__ = []
        boto3_s3 = types.ModuleType("boto3.s3")
        boto3_s3.__path__ = []
        transfer = types.ModuleType("boto3.s3.transfer")
        transfer.S3UploadFailedError = type("S3UploadFailedError", (Exception,), {})
        botocore = types.ModuleType("botocore")
        botocore.__path__ = []
        exceptions = types.ModuleType("botocore.exceptions")
        exceptions.BotoCoreError = type("BotoCoreError", (Exception,), {})
        exceptions.ClientError = type("ClientError", (Exception,), {})
        with (
            patch.dict(
                os.environ,
                {
                    "BACKUP_ENCRYPTION_KEY": key,
                    "S3_BACKUP_BUCKET": "private-backups",
                    "S3_BACKUP_PREFIX": "platform/prod",
                },
            ),
            patch.dict(
                sys.modules,
                {
                    "boto3": boto3,
                    "boto3.s3": boto3_s3,
                    "boto3.s3.transfer": transfer,
                    "botocore": botocore,
                    "botocore.exceptions": exceptions,
                },
            ),
        ):
            call_command(
                "backup_platform",
                output_dir=str(self.test_backup_dir),
                no_media=True,
                encrypt=True,
                upload=True,
            )

        uploaded_keys = {call.args[2] for call in s3.upload_file.call_args_list}
        archive = next(self.test_backup_dir.glob("*.tar.gz.enc"))
        boto3.client.assert_called_once_with("s3", endpoint_url=None, region_name="us-east-1")
        self.assertEqual(
            uploaded_keys,
            {
                f"platform/prod/{archive.name}",
                f"platform/prod/{archive.name}.sha256",
            },
        )

    def test_upload_requires_bucket(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("S3_BACKUP_BUCKET", None)
            with self.assertRaisesMessage(CommandError, "S3_BACKUP_BUCKET"):
                call_command(
                    "backup_platform",
                    output_dir=str(self.test_backup_dir),
                    no_media=True,
                    encrypt=True,
                    upload=True,
                )

    def test_upload_rejects_plaintext_archive(self):
        with (
            patch.dict(os.environ, {"S3_BACKUP_BUCKET": "private-backups"}),
            self.assertRaisesMessage(CommandError, "unencrypted archive"),
        ):
            call_command(
                "backup_platform",
                output_dir=str(self.test_backup_dir),
                no_media=True,
                upload=True,
            )


class CeleryBeatBackupTests(TestCase):
    """Verify scheduled daily backup task and schedule."""

    @classmethod
    def setUpTestData(cls):
        from django_celery_beat.models import IntervalSchedule, PeriodicTask

        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.DAYS,
        )
        PeriodicTask.objects.get_or_create(
            name="Daily Platform Backup",
            defaults={
                "task": "apps.core.tasks.daily_backup",
                "interval": schedule,
                "enabled": True,
            },
        )

    def test_daily_backup_schedule_exists(self):
        """IntervalSchedule and PeriodicTask for daily backup must exist."""
        from django_celery_beat.models import IntervalSchedule, PeriodicTask

        schedule_exists = IntervalSchedule.objects.filter(every=1, period=IntervalSchedule.DAYS).exists()
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
            encrypt=True,
            upload=True,
        )
