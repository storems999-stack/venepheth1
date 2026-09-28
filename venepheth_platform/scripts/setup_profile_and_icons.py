"""
Script to set venepheth profile photo and generate app icons from venepheth.jpg
"""

import os
import sys
from pathlib import Path

import django
from PIL import Image

# Initialize Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.core.files import File

from apps.profiles.models import Profile

SOURCE_IMAGE = BASE_DIR / "venepheth.jpg"
STATIC_ICONS_DIR = BASE_DIR / "static" / "icons"
STATIC_DIR = BASE_DIR / "static"
STATICFILES_DIR = BASE_DIR / "staticfiles"


def generate_icons():
    STATIC_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    STATICFILES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Opening source image: {SOURCE_IMAGE}")
    im = Image.open(SOURCE_IMAGE)
    # Convert RGBA or CMYK to RGB if needed
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")

    # 1. Favicon sizes
    sizes = [
        ("favicon-16x16.png", (16, 16)),
        ("favicon-32x32.png", (32, 32)),
        ("favicon-48x48.png", (48, 48)),
        ("apple-touch-icon.png", (180, 180)),
        ("icon-192.png", (192, 192)),
        ("icon-512.png", (512, 512)),
        ("app_icon.png", (512, 512)),
    ]

    for filename, size in sizes:
        resized = im.resize(size, Image.Resampling.LANCZOS)
        out_path = STATIC_ICONS_DIR / filename
        resized.save(out_path, format="PNG")
        print(f"Generated: {out_path} ({size[0]}x{size[1]})")

    # 2. Favicon .ico containing multiple resolutions
    ico_path = STATIC_ICONS_DIR / "favicon.ico"
    im.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f"Generated: {ico_path}")

    # Copy favicon.ico to root static/ and staticfiles/
    import shutil

    shutil.copy2(ico_path, STATIC_DIR / "favicon.ico")
    shutil.copy2(ico_path, STATICFILES_DIR / "favicon.ico")
    print(f"Copied favicon.ico to {STATIC_DIR / 'favicon.ico'} and {STATICFILES_DIR / 'favicon.ico'}")

    # Also copy app_icon.png to static/ for quick access
    shutil.copy2(STATIC_ICONS_DIR / "app_icon.png", STATIC_DIR / "app_icon.png")

    # 3. Create site.webmanifest
    manifest_content = """{
  "name": "Venepheth SAYAVONG Platform",
  "short_name": "Venepheth",
  "icons": [
    {
      "src": "/static/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "theme_color": "#0d1f35",
  "background_color": "#0d1f35",
  "display": "standalone",
  "start_url": "/"
}
"""
    with open(STATIC_DIR / "site.webmanifest", "w", encoding="utf-8") as f:
        f.write(manifest_content)
    print("Generated site.webmanifest")


def update_profile():
    profile = Profile.objects.first()
    if not profile:
        print("No profile found! Creating default Venepheth profile...")
        profile = Profile(
            full_name="Venepheth SAYAVONG", title="Lecturer & Researcher in Business Administration", is_active=True
        )

    with open(SOURCE_IMAGE, "rb") as f:
        profile.photo.save("venepheth.jpg", File(f), save=True)

    profile.save()
    print(f"Successfully updated Profile photo: {profile.photo.name}")
    print(f"Photo URL: {profile.photo.url}")


if __name__ == "__main__":
    generate_icons()
    update_profile()
    print("Done!")
