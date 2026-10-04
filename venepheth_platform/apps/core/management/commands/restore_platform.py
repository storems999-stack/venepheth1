"""
Disaster Recovery Platform Restore Command.
Restores database and media assets from an automated backup archive with
checksum integrity verification.
"""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tarfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

try:
    from cryptography.fernet import Fernet, InvalidToken

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


def _remove_unsupported_pg17_settings(sql: str, server_version_num: int) -> tuple[str, int]:
    """Remove the PG17-only default timeout setting when restoring to older servers."""
    if server_version_num >= 170000:
        return sql, 0
    return re.subn(
        r"(?im)^[ \t]*SET[ \t]+transaction_timeout[ \t]*=[ \t]*0[ \t]*;[ \t]*$",
        "-- transaction_timeout is not supported before PostgreSQL 17",
        sql,
    )


def _decrypt_archive(archive_path: Path) -> Path:
    """Decrypt a Fernet-encrypted archive. Returns the decrypted path.

    Key resolution mirrors backup_platform._get_encryption_key so the same
    BACKUP_ENCRYPTION_KEY (or backup_key.bin) decrypts what the backup wrote.
    """
    env_key = os.environ.get("BACKUP_ENCRYPTION_KEY", "").strip()
    if env_key:
        key = env_key.encode()
    else:
        key_path = Path(settings.BASE_DIR) / "backup_key.bin"
        if not key_path.exists():
            raise CommandError(
                f"{archive_path.name} is encrypted but no key is available. Set "
                "BACKUP_ENCRYPTION_KEY in the environment or restore backup_key.bin."
            )
        key = key_path.read_bytes().strip()

    try:
        decrypted = Fernet(key).decrypt(archive_path.read_bytes())
    except InvalidToken as exc:
        raise CommandError(f"Decryption failed for {archive_path.name}: wrong or corrupt key.") from exc

    decrypted_path = archive_path.with_name(archive_path.name.removesuffix(".enc"))
    decrypted_path.write_bytes(decrypted)
    return decrypted_path


class Command(BaseCommand):
    help = "Restores the platform database and media assets from a verified backup archive."

    def add_arguments(self, parser):
        parser.add_argument(
            "--archive",
            type=str,
            help="Path to the backup .tar.gz archive (default: latest archive in <BASE_DIR>/backups)",
        )
        parser.add_argument(
            "--no-checksum",
            action="store_true",
            help="Skip SHA256 checksum verification",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm restoration without interactive prompt (database is flushed before portable restore)",
        )
        parser.add_argument(
            "--verify-only",
            action="store_true",
            help="Verify checksum and contents without altering database or media files",
        )

    def handle(self, *args, **options):
        archive_path_arg = options.get("archive")
        skip_checksum = options.get("no_checksum", False)
        confirm = options.get("confirm", False)

        backups_dir = settings.BASE_DIR / "backups"

        if archive_path_arg:
            archive_path = Path(archive_path_arg)
        else:
            # Find latest archive — match both plain (.tar.gz) and encrypted
            # (.tar.gz.enc) files, ignoring the .sha256 sidecars.
            archives = sorted(
                (
                    p
                    for p in backups_dir.glob("backup_venepheth_platform_*.tar.gz*")
                    if p.suffix != ".sha256" and p.is_file()
                ),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not archives:
                raise CommandError(f"No backup archives found in {backups_dir}. Specify --archive path.")
            archive_path = archives[0]

        if not archive_path.exists():
            raise CommandError(f"Backup archive does not exist: {archive_path}")

        self.stdout.write(self.style.NOTICE(f"[*] Preparing restore from: {archive_path.name}"))

        # 1. Checksum verification — MUST run on the on-disk bytes, i.e. before
        # decryption (the .sha256 sidecar hashes the encrypted archive).
        checksum_path = archive_path.with_name(f"{archive_path.name}.sha256")
        if checksum_path.exists() and not skip_checksum:
            self.stdout.write("    -> Verifying SHA256 integrity checksum...")
            try:
                with open(checksum_path, "r", encoding="utf-8") as f:
                    checksum_parts = f.read().split()
            except (OSError, UnicodeError) as exc:
                raise CommandError(f"Could not read checksum sidecar {checksum_path}: {exc}") from exc
            if not checksum_parts:
                raise CommandError(f"Integrity Check Failed: checksum sidecar is empty ({checksum_path}).")
            expected_sha = checksum_parts[0].strip().lower()

            sha256 = hashlib.sha256()
            with open(archive_path, "rb") as f:
                while chunk := f.read(65536):
                    sha256.update(chunk)
            actual_sha = sha256.hexdigest().lower()

            if actual_sha != expected_sha:
                raise CommandError(f"Integrity Check Failed!\nExpected: {expected_sha}\nActual:   {actual_sha}")
            self.stdout.write(self.style.SUCCESS("    -> Checksum verified: OK"))
        elif not skip_checksum:
            self.stdout.write(self.style.WARNING("    [!] No checksum sidecar found — archive integrity NOT verified."))

        verify_only = options.get("verify_only", False)
        if not confirm and not verify_only:
            prompt = input("⚠️  WARNING: Restoring will overwrite existing data. Type 'yes' to proceed: ")
            if prompt.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING("Restore cancelled by user."))
                return

        # 2. Decrypt (after integrity verification, before extraction).
        decrypted_path = None
        if archive_path.name.endswith(".enc"):
            if not HAS_CRYPTOGRAPHY:
                raise CommandError("Archive is encrypted but cryptography is not installed.")
            self.stdout.write("    -> Decrypting encrypted archive...")
            # _decrypt_archive writes the plaintext tar.gz next to the
            # encrypted original; keep the path so it can be removed after
            # the restore instead of lingering as a plaintext DB dump.
            decrypted_path = _decrypt_archive(archive_path)
            archive_path = decrypted_path
            self.stdout.write(self.style.SUCCESS("    -> Decryption complete."))

        staging_dir = backups_dir / f"restore_staging_{archive_path.stem}"
        staging_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(staging_dir, 0o700)
        except OSError as exc:
            self.stderr.write(self.style.WARNING(f"    [!] Could not restrict restore staging permissions ({exc})."))

        try:
            # 2. Extract Archive
            self.stdout.write("    -> Extracting archive...")
            try:
                with tarfile.open(archive_path, "r:gz") as tar:
                    # Reject path traversal / unsafe members (Bandit B202, PEP 706).
                    tar.extractall(path=staging_dir, filter="data")
            except (OSError, tarfile.TarError) as exc:
                raise CommandError(f"Backup archive contents could not be read: {exc}") from exc

            manifest = None
            manifest_file = staging_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                except (OSError, json.JSONDecodeError) as exc:
                    raise CommandError(f"Backup manifest is unreadable: {exc}") from exc
                if not isinstance(manifest, dict):
                    raise CommandError("Backup manifest is invalid: expected a JSON object.")
                self.stdout.write(f"    -> Manifest: Created at {manifest.get('created_at', 'unknown')}")

            if verify_only:
                if manifest is None:
                    raise CommandError("Backup contents are invalid: a readable manifest.json is required.")
                database_dumps = (
                    staging_dir / "db.sqlite3",
                    staging_dir / "postgres.dump",
                    staging_dir / "data_dump.json",
                )
                if not any(path.is_file() and path.stat().st_size > 0 for path in database_dumps):
                    raise CommandError("Backup contents are invalid: no non-empty database dump was found.")
                sqlite_dump = staging_dir / "db.sqlite3"
                if sqlite_dump.exists():
                    try:
                        sqlite_uri = f"file:{sqlite_dump.resolve().as_posix()}?mode=ro"
                        with sqlite3.connect(sqlite_uri, uri=True) as sqlite_db:
                            check_result = sqlite_db.execute("PRAGMA quick_check").fetchone()
                    except sqlite3.Error as exc:
                        raise CommandError(f"SQLite database dump is unreadable: {exc}") from exc
                    if not check_result or check_result[0] != "ok":
                        raise CommandError("SQLite database dump failed its integrity check.")
                postgres_dump = staging_dir / "postgres.dump"
                if postgres_dump.exists():
                    try:
                        result = subprocess.run(
                            ["pg_restore", "--list", str(postgres_dump)],
                            check=False,
                            capture_output=True,
                            text=True,
                        )
                    except OSError as exc:
                        raise CommandError(f"Could not inspect PostgreSQL dump: {exc}") from exc
                    if result.returncode != 0:
                        detail = (result.stderr or result.stdout or "").strip()
                        raise CommandError(f"PostgreSQL database dump is unreadable: {detail}")
                data_dump = staging_dir / "data_dump.json"
                if data_dump.exists():
                    try:
                        with data_dump.open(encoding="utf-8") as dump_file:
                            data = json.load(dump_file)
                    except (OSError, json.JSONDecodeError) as exc:
                        raise CommandError(f"Portable database dump is unreadable: {exc}") from exc
                    if not isinstance(data, list):
                        raise CommandError("Portable database dump is invalid: expected a JSON array.")
                self.stdout.write(self.style.SUCCESS("[+] Integrity and archive contents verified! (No changes made)"))
                return

            # 3. Restore Media files
            staged_media = staging_dir / "media"
            if staged_media.exists():
                self.stdout.write("    -> Restoring media uploads...")
                media_root = Path(settings.MEDIA_ROOT)
                media_root.mkdir(parents=True, exist_ok=True)
                shutil.copytree(staged_media, media_root, dirs_exist_ok=True)

            # 4. Restore Database
            db_conn = settings.DATABASES["default"]
            engine = db_conn["ENGINE"]
            staged_sqlite = staging_dir / "db.sqlite3"
            staged_json = staging_dir / "data_dump.json"
            staged_pg = staging_dir / "postgres.dump"

            if "postgresql" in engine and staged_pg.exists():
                self.stdout.write("    -> Preparing a transactional PostgreSQL restore...")
                env = os.environ.copy()
                if db_conn.get("PASSWORD"):
                    env["PGPASSWORD"] = db_conn["PASSWORD"]
                restore_sql = staging_dir / "postgres_restore.sql"
                fd = os.open(restore_sql, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                generated = subprocess.run(
                    [
                        "pg_restore",
                        "--clean",
                        "--if-exists",
                        "--file",
                        str(restore_sql),
                        str(staged_pg),
                    ],
                    env=env,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if generated.returncode != 0:
                    detail = (generated.stderr or generated.stdout or "").strip()
                    raise CommandError(f"pg_restore could not generate a restore script.\n{detail}")

                with connection.cursor() as cursor:
                    cursor.execute("SHOW server_version_num")
                    server_version_num = int(cursor.fetchone()[0])
                restore_text = restore_sql.read_text(encoding="utf-8")
                restore_text, removed_settings = _remove_unsupported_pg17_settings(
                    restore_text,
                    server_version_num,
                )
                if removed_settings:
                    restore_sql.write_text(restore_text, encoding="utf-8")
                    self.stdout.write(
                        self.style.NOTICE(
                            f"    -> Removed {removed_settings} PG17-only timeout setting(s) for this server."
                        )
                    )

                result = subprocess.run(
                    [
                        "psql",
                        "--no-psqlrc",
                        "--single-transaction",
                        "--set",
                        "ON_ERROR_STOP=1",
                        "-h",
                        db_conn.get("HOST", "localhost"),
                        "-p",
                        str(db_conn.get("PORT", 5432)),
                        "-U",
                        db_conn.get("USER", "postgres"),
                        "-d",
                        db_conn["NAME"],
                        "--file",
                        str(restore_sql),
                    ],
                    env=env,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    detail = (result.stderr or result.stdout or "").strip()
                    raise CommandError(
                        f"Transactional PostgreSQL restore failed (exit {result.returncode}).\n"
                        f"{detail}\nThe transaction was rolled back; the database was not partially restored."
                    )
            elif "sqlite3" in engine and staged_sqlite.exists():
                self.stdout.write("    -> Restoring SQLite database snapshot...")
                dest_sqlite = Path(db_conn["NAME"])
                with sqlite3.connect(str(staged_sqlite)) as src, sqlite3.connect(str(dest_sqlite)) as dst:
                    src.backup(dst)
            elif staged_json.exists():
                # flush + loaddata MUST be one transaction. Run separately, a
                # failure midway through loaddata leaves production empty —
                # the worst possible outcome for a disaster-recovery tool.
                self.stdout.write("    -> Restoring portable dump (flush + loaddata in one transaction)...")
                from django.db import transaction

                with transaction.atomic():
                    call_command("flush", "--no-input")
                    call_command("loaddata", str(staged_json))
            else:
                self.stdout.write(self.style.WARNING("    [!] No compatible database dump found in archive."))

            self.stdout.write(self.style.SUCCESS("[+] Platform restored successfully!"))

        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
            # The decrypted .tar.gz must not outlive the restore — it is a
            # full plaintext database dump sitting next to the encrypted one.
            if decrypted_path is not None:
                try:
                    if decrypted_path.exists() and decrypted_path != archive_path:
                        decrypted_path.unlink()
                        self.stdout.write(f"    -> Removed decrypted archive {decrypted_path.name}")
                except OSError as exc:
                    self.stderr.write(
                        self.style.WARNING(
                            f"    [!] Could not remove decrypted archive {decrypted_path}: {exc}. "
                            "Delete it manually — it contains an unencrypted database dump."
                        )
                    )
