"""Helpers for admin actions that must retain model save/history behavior."""

from django.db import transaction


def save_queryset_with_history(queryset, request, **updates):
    """Apply field changes with normal model saves and history for each row."""
    if not updates:
        return 0

    count = 0
    with transaction.atomic():
        for instance in queryset.select_for_update().iterator():
            for field, value in updates.items():
                setattr(instance, field, value)
            user = getattr(request, "user", None)
            if user is not None:
                instance._history_user = user
            instance.save(update_fields=(*updates, "updated_at"))
            count += 1
    return count
