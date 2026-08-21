"""Models package."""
from __future__ import annotations

from src.models.user import (
    VALID_ROLES,
    User,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user,
    set_user_active,
    delete_user,
    list_users,
)
from src.models.notifications import (
    Notification,
    create_notification,
    get_notifications_by_user,
    get_unread_count,
    mark_notification_read,
    mark_all_read,
)

__all__ = [
    "VALID_ROLES",
    "User",
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "update_user",
    "set_user_active",
    "delete_user",
    "list_users",
    "Notification",
    "create_notification",
    "get_notifications_by_user",
    "get_unread_count",
    "mark_notification_read",
    "mark_all_read",
]