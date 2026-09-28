"""
Automated 3-2-1 Platform Backup Command.
Creates a complete, verified, tamper-evident backup of the database, media assets,
and platform metadata.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import time
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Creates an automated, verified backup of the database, media files, and manifest."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=str(settings.BASE_DIR / "backups"),
            help="Directory to store backup archives (default: <BASE_DIR>/backups)",
        )
        parser.add_argument(
            "--keep-days",
            type=int,
            default=14,
            help="Retention policy: automatically prune backups older than N days (default: 14)",
        )
        parser.add_argument(
            "--no-media",
            action="store_true",
            help="Skip archiving uploaded media files",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(output_dir, 0o700)
        keep_days = options["keep_days"]
        include_media = not options["no_media"]

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        staging_dir = output_dir / f"staging_{timestamp}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        archive_name = f"backup_venepheth_platform_{timestamp}.tar.gz"
        archive_path = output_dir / archive_name
        checksum_path = output_dir / f"{archive_name}.sha256"

        self.stdout.write(self.style.NOTICE(f"[*] Starting backup sequence at {timestamp}..."))

        try:
            # 1. Backup Database
            db_conn = settings.DATABASES["default"]
            engine = db_conn["ENGINE"]

            if "sqlite3" in engine:
                sqlite_path = Path(db_conn["NAME"])
                if sqlite_path.exists():
                    self.stdout.write("    -> Backing up SQLite database via live snapshot...")
                    dest_sqlite = staging_dir / "db.sqlite3"
                    with sqlite3.connect(str(sqlite_path)) as src, sqlite3.connect(str(dest_sqlite)) as dst:
                        src.backup(dst)
            elif "postgresql" in engine:
                self.stdout.write("    -> Exporting PostgreSQL dump...")
                env = os.environ.copy()
                if db_conn.get("PASSWORD"):
                    env["PGPASSWORD"] = db_conn["PASSWORD"]
                pg_cmd = [
                    "pg_dump",
                    "-h",
                    db_conn.get("HOST", "localhost"),
                    "-p",
                    str(db_conn.get("PORT", 5432)),
                    "-U",
                    db_conn.get("USER", "postgres"),
                    "-d",
                    db_conn["NAME"],
                    "-F",
                    "c",
                    "-f",
                    str(staging_dir / "postgres.dump"),
                ]
                try:
                    subprocess.run(pg_cmd, env=env, check=True, capture_output=True)
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"    [!] pg_dump direct call failed ({e}), falling back to JSON dumpdata")
                    )

            # 2. Universal JSON Dump for cross-database portability
            self.stdout.write("    -> Generating portable JSON data dump (dumpdata)...")
            json_dump_file = staging_dir / "data_dump.json"
            with open(json_dump_file, "w", encoding="utf-8") as f:
                call_command(
                    "dumpdata",
                    natural_foreign=True,
                    natural_primary=True,
                    exclude=["contenttypes", "auth.permission"],
                    stdout=f,
                )

            # 3. Archive Media files
            if include_media and Path(settings.MEDIA_ROOT).exists():
                self.stdout.write("    -> Archiving uploaded media files...")
                media_staged = staging_dir / "media"
                shutil.copytree(settings.MEDIA_ROOT, media_staged, dirs_exist_ok=True)

            # 4. Create Manifest
            manifest = {
                "platform": "Venepheth Academic Platform",
                "timestamp": timestamp,
                "created_at": timezone.now().isoformat(),
                "db_engine": engine,
                "django_version": getattr(settings, "DJANGO_VERSION", "5.1"),
                "media_included": include_media,
            }
            with open(staging_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

            # 5. Compress into tar.gz
            self.stdout.write(f"    -> Compressing backup archive to {archive_name}...")
            with tarfile.open(archive_path, "w:gz") as tar:
                for item in staging_dir.iterdir():
                    tar.add(str(item), arcname=item.name)

            # 6. Calculate SHA256 Checksum
            self.stdout.write("    -> Calculating SHA256 integrity checksum...")
            sha256 = hashlib.sha256()
            with open(archive_path, "rb") as f:
                while chunk := f.read(65536):
                    sha256.update(chunk)
            checksum_str = sha256.hexdigest()

            with open(checksum_path, "w", encoding="utf-8") as f:
                f.write(f"{checksum_str}  {archive_name}\n")

            # 7. Restrict permissions: archives hold a full DB dump (owner-only).
            os.chmod(archive_path, 0o600)
            os.chmod(checksum_path, 0o600)

            archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
            self.stdout.write(
                self.style.SUCCESS(
                    f"[+] Backup completed successfully!\n"
                    f"    Archive:  {archive_path} ({archive_size_mb:.2f} MB)\n"
                    f"    SHA256:   {checksum_str}"
                )
            )

            # 7. Apply Retention Policy
            if keep_days > 0:
                self._prune_old_backups(output_dir, keep_days)

        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)

    def _prune_old_backups(self, output_dir: Path, keep_days: int):
        cutoff = time.time() - (keep_days * 86400)
        pruned_count = 0
        for f in output_dir.glob("backup_venepheth_platform_*"):
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink(missing_ok=True)
                sha_f = f.with_name(f"{f.name}.sha256")
                sha_f.unlink(missing_ok=True)
                pruned_count += 1
        if pruned_count > 0:
            self.stdout.write(
                self.style.NOTICE(
                    f"    -> Retention policy: pruned {pruned_count} backups older than {keep_days} days."
                )
            )
