#!/usr/bin/env bash
# ==============================================================================
# Venepheth Academic Platform - Disaster Recovery Restore Script
# Conforms to Disaster Recovery Architecture (Section 35, vision.txt)
#
# Supports Fernet-encrypted (.enc) archives. Decryption is performed by
# `manage.py restore_platform`, which resolves the key from
# BACKUP_ENCRYPTION_KEY (or <BASE_DIR>/backup_key.bin) — do NOT try to
# decrypt here: Fernet is not openssl enc.
# ==============================================================================
set -euo pipefail

# Always run from the project root. Under cron (or any absolute-path
# invocation) the current directory is $HOME, where manage.py does not exist.
cd "$(dirname "$0")/.."

ARCHIVE="${1:-}"

if [ -z "$ARCHIVE" ]; then
    echo "Usage: $0 /path/to/backup_archive.tar.gz[.enc]"
    echo "Example: $0 /app/backups/backup_venepheth_platform_20260922_150000.tar.gz.enc"
    echo ""
    echo "Omit the path to restore the most recent archive automatically."
    exit 1
fi

if [ ! -f "$ARCHIVE" ]; then
    echo "ERROR: Archive not found: $ARCHIVE"
    exit 1
fi

# For encrypted archives, fail fast with a clear message if no key is set.
case "$ARCHIVE" in
    *.enc)
        if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ] && [ ! -f "$(dirname "$0")/../backup_key.bin" ]; then
            echo "ERROR: $ARCHIVE is encrypted but no key is available."
            echo "       Set BACKUP_ENCRYPTION_KEY, or restore backup_key.bin."
            echo "       Generate a key with: python manage.py generate_backup_key"
            exit 1
        fi
        ;;
esac

echo "=================================================="
echo " Starting Disaster Recovery Restore: $(date)"
echo " Archive: ${ARCHIVE}"
echo "=================================================="

python manage.py restore_platform --archive "${ARCHIVE}" --confirm

# A crashed restore can leave the decrypted .tar.gz next to the encrypted
# archive — that file is a full plaintext database dump.
if [ "${ARCHIVE%.enc}" != "$ARCHIVE" ] && [ -f "${ARCHIVE%.enc}" ]; then
    rm -f "${ARCHIVE%.enc}"
    echo "Removed decrypted archive: ${ARCHIVE%.enc}"
fi

echo "=================================================="
echo " Platform Restore Complete: $(date)"
echo "=================================================="
