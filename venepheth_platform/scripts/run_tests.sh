#!/usr/bin/env bash
# Run the Django test suite with a supported Python (3.14 preferred; avoids 3.15 beta issues).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pick_python() {
  for ver in 3.14 3.12 3.13 3.11; do
    if command -v "python${ver}" >/dev/null 2>&1; then
      echo "python${ver}"
      return
    fi
  done
  if command -v py >/dev/null 2>&1; then
    for ver in 3.14 3.12 3.13 3.11; do
      if py "-${ver}" -c "import sys" 2>/dev/null; then
        echo "py -${ver}"
        return
      fi
    done
  fi
  echo "No supported Python (3.11+) found. Install 3.14 if possible." >&2
  exit 1
}

PY="$(pick_python)"
echo "Using $PY (.python-version recommends 3.14)"

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.testing}"
export SECRET_KEY="${SECRET_KEY:-local-test-secret}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-localhost,127.0.0.1,testserver}"

exec $PY -m pytest tests/ -v --tb=short "$@"
