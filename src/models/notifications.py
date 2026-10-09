"""Notification model and data access layer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from src.models.user import _is_postgres_db


@dataclass
class Notification:
    """Notification model."""
    id: int
    user_id: int
    message: str
    is_read: bool
    created_at: str
    prescription_id: Optional[int]

    @classmethod
    def from_row(cls, row: Any) -> "Notification":
        """Create Notification from database row."""
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            message=row["message"],
            is_read=bool(row["is_read"]),
            created_at=row["created_at"],
            prescription_id=row["prescription_id"] if row["prescription_id"] is not None else None,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at,
            "prescription_id": self.prescription_id,
        }


def get_current_timestamp() -> str:
    """Get current UTC timestamp as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


def create_notification(
    db: Any,
    user_id: int,
    message: str,
    prescription_id: Optional[int] = None,
) -> Notification:
    """Create a new notification."""
    now = get_current_timestamp()
    cursor = db.cursor()
    if _is_postgres_db(db):
        # psycopg2 does NOT populate cursor.lastrowid (it stays 0), so read the
        # new primary key back via INSERT ... RETURNING id. The PSQL cursor
        # wrapper converts ? placeholders to %s, so RETURNING id is preserved.
        cursor.execute(
            """
            INSERT INTO notifications (user_id, message, is_read, created_at, prescription_id)
            VALUES (?, ?, 0, ?, ?) RETURNING id
            """,
            (user_id, message, now, prescription_id),
        )
        row = cursor.fetchone()
        db.commit()
        if not row:
            notification_id = 0
        else:
            # RealDictCursor (app path) yields dict-like rows; a plain psycopg2
            # cursor yields tuples. Support both.
            notification_id = row["id"] if isinstance(row, dict) else row[0]
            notification_id = int(notification_id)
    else:
        cursor.execute(
            """
            INSERT INTO notifications (user_id, message, is_read, created_at, prescription_id)
            VALUES (?, ?, 0, ?, ?)
            """,
            (user_id, message, now, prescription_id),
        )
        db.commit()
        notification_id = cursor.lastrowid

    return Notification(
        id=notification_id,
        user_id=user_id,
        message=message,
        is_read=False,
        created_at=now,
        prescription_id=prescription_id,
    )


def get_notifications_by_user(db: Any, user_id: int, unread_only: bool = False) -> list[Notification]:
    """Get notifications for a user."""
    cursor = db.cursor()
    if unread_only:
        cursor.execute(
            "SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC",
            (user_id,),
        )
    else:
        cursor.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
    return [Notification.from_row(row) for row in cursor.fetchall()]


def get_unread_count(db: Any, user_id: int) -> int:
    """Get count of unread notifications for a user."""
    cursor = db.cursor()
    cursor.execute(
        "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0",
        (user_id,),
    )
    return cursor.fetchone()["count"]


def mark_notification_read(db: Any, notification_id: int, user_id: int) -> bool:
    """Mark a notification as read."""
    cursor = db.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
        (notification_id, user_id),
    )
    db.commit()
    return cursor.rowcount > 0


def mark_all_read(db: Any, user_id: int) -> int:
    """Mark all notifications as read for a user."""
    cursor = db.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
        (user_id,),
    )
    db.commit()
    return cursor.rowcount