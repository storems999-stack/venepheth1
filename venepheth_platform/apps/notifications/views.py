"""
Notifications views with HTMX support.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Notification


@login_required
def notification_list(request):
    """Display all notifications for the authenticated user."""
    notifications = request.user.notifications.all()
    unread_count = notifications.filter(is_read=False).count()
    return render(
        request,
        "notifications/list.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


@login_required
@require_GET
def unread_badge(request):
    """HTMX endpoint returning the notification badge snippet."""
    count = request.user.notifications.filter(is_read=False).count()
    return render(
        request,
        "notifications/partials/badge.html",
        {"count": count},
    )


@login_required
@require_POST
def mark_as_read(request, pk):
    """Mark a specific notification as read."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read", "updated_at"])

    if request.headers.get("HX-Request"):
        return render(
            request,
            "notifications/partials/notification_item.html",
            {"notification": notification},
        )
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_as_read(request):
    """Mark all notifications for the user as read."""
    request.user.notifications.filter(is_read=False).update(is_read=True, updated_at=timezone.now())

    if request.headers.get("HX-Request"):
        notifications = request.user.notifications.all()
        return render(
            request,
            "notifications/partials/notification_list_body.html",
            {"notifications": notifications, "unread_count": 0},
        )
    return redirect("notifications:list")
