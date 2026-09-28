"""Contact views with honeypot anti-spam and notification email."""

import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from .forms import ContactForm
from .models import ContactMessage

logger = logging.getLogger("apps.contact")


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
@require_http_methods(["GET", "POST"])
def contact_form(request):
    """Contact form page supporting honeypot anti-spam and HTMX submissions."""
    is_htmx = bool(request.headers.get("HX-Request"))

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            from apps.core.utils import get_client_ip

            contact_msg = form.save(commit=False)
            contact_msg.ip_address = get_client_ip(request)
            contact_msg.user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]

            # Check honeypot
            if getattr(form, "is_spam", False):
                logger.warning("Spam bot submission caught by honeypot: %s (%s)", contact_msg.name, contact_msg.email)
                contact_msg.status = ContactMessage.Status.SPAM
                contact_msg.save()
            else:
                contact_msg.status = ContactMessage.Status.NEW
                contact_msg.save()

                # Dispatch notification email (fail-closed: never claim success if it fails).
                try:
                    admin_email = settings.DEFAULT_FROM_EMAIL
                    subject = f"[Contact Form] {contact_msg.subject} from {contact_msg.name}"
                    plain_message = (
                        f"New inquiry received from website:\n\n"
                        f"Name: {contact_msg.name}\n"
                        f"Email: {contact_msg.email}\n"
                        f"Organization: {contact_msg.organization or 'N/A'}\n"
                        f"Subject: {contact_msg.subject}\n\n"
                        f"Message:\n{contact_msg.message}\n"
                    )
                    from django.template.loader import render_to_string

                    html_message = render_to_string(
                        "contact/emails/notification.html",
                        {"contact_msg": contact_msg, "subject": subject},
                    )
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=admin_email,
                        recipient_list=[admin_email],
                        fail_silently=False,
                    )
                except Exception as mail_err:
                    # Message is already saved — tell the visitor the truth instead
                    # of redirecting to the success page.
                    logger.warning("Failed to send contact notification email: %s", mail_err)
                    messages.error(
                        request,
                        _(
                            "Your message was saved and will be reviewed, "
                            "but the email notification failed. Please try again later if urgent."
                        ),
                    )
                    return render(
                        request,
                        "contact/form.html",
                        {
                            "form": ContactForm(),
                            "meta_title": _("Contact"),
                            "meta_description": _(
                                "Get in touch with Venepheth Sayavong for academic inquiries and collaboration."
                            ),
                        },
                    )

            if is_htmx:
                return render(request, "contact/partials/success_inline.html")

            messages.success(request, _("Thank you! Your message has been sent successfully."))
            return redirect("contact:success")
        else:
            if not is_htmx:
                messages.error(request, _("Please correct the errors below and try again."))
    else:
        form = ContactForm()

    return render(
        request,
        "contact/form.html",
        {
            "form": form,
            "meta_title": _("Contact"),
            "meta_description": _("Get in touch with Venepheth Sayavong for academic inquiries and collaboration."),
        },
    )


def contact_success(request):
    """Contact success page."""
    return render(
        request,
        "contact/success.html",
        {
            "meta_title": _("Message Sent"),
        },
    )
