"""
Generate a Fernet key for encrypting backup archives.

The key is the single secret that protects every encrypted backup — losing it
makes those archives permanently unrecoverable. This command exists so key
creation is always a deliberate operator action, never a side effect of a
scheduled backup run.

Usage:
    python manage.py generate_backup_key            # print a key
    python manage.py generate_backup_key --write    # also write backup_key.bin (0600)
"""

import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Generates a Fernet key for encrypting backup archives."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write",
            action="store_true",
            help="Write the key to <BASE_DIR>/backup_key.bin with 0600 permissions (local use only).",
        )

    def handle(self, *args, **options):
        try:
            from cryptography.fernet import Fernet
        except ImportError as exc:
            raise CommandError("cryptography is not installed.") from exc

        key = Fernet.generate_key()
        text = key.decode()

        if options["write"]:
            key_path = Path(settings.BASE_DIR) / "backup_key.bin"
            if key_path.exists():
                raise CommandError(
                    f"{key_path} already exists. Refusing to overwrite — doing so would make "
                    "every archive encrypted with the old key unrecoverable."
                )
            key_path.write_bytes(key)
            os.chmod(key_path, 0o600)
            self.stdout.write(self.style.SUCCESS(f"Key written to {key_path} (mode 0600)."))

        self.stdout.write("")
        self.stdout.write("Backup encryption key (Fernet):")
        self.stdout.write(f"  {text}")
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Store this offline and separately from the backups. It is required to decrypt "
                "them. Put it in BACKUP_ENCRYPTION_KEY in .env.prod, and keep a printed copy."
            )
        )
