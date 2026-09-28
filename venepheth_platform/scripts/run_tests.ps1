# Run the Django test suite with a supported Python (3.14 preferred; avoids 3.15 beta issues).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Get-TestPython {
    foreach ($ver in @("3.14", "3.12", "3.13", "3.11")) {
        try {
            & py "-$ver" -c "import sys; sys.exit(0)" 2>$null
            if ($LASTEXITCODE -eq 0) { return $ver }
        } catch {}
    }
    throw "No supported Python found. Install 3.11+ (recommended: 3.14)."
}

$pyVer = Get-TestPython
Write-Host "Using Python $pyVer (see .python-version)" -ForegroundColor Cyan

$env:DJANGO_SETTINGS_MODULE = "config.settings.testing"
if (-not $env:SECRET_KEY) { $env:SECRET_KEY = "local-test-secret" }
if (-not $env:ALLOWED_HOSTS) { $env:ALLOWED_HOSTS = "localhost,127.0.0.1,testserver" }

& py "-$pyVer" -m pytest tests/ -v --tb=short @args
exit $LASTEXITCODE
