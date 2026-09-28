from django.conf import settings
from django.shortcuts import render


def privacy_policy(request):
    """Privacy Policy page (vision para 45)."""
    context = {
        "meta_title": "Privacy Policy" + " \u2014 " + settings.SITE_NAME,
        "meta_description": "How we collect, use, and protect your data.",
    }
    return render(request, "core/privacy.html", context)


def terms_of_use(request):
    """Terms of Use page."""
    context = {
        "meta_title": "Terms of Use" + " \u2014 " + settings.SITE_NAME,
        "meta_description": "Terms and conditions for using this platform.",
    }
    return render(request, "core/terms.html", context)
