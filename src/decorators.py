"""Authentication decorators."""
from __future__ import annotations

from functools import wraps

from flask import flash, redirect, session, url_for


VALID_ROLES = {"doctor", "pharmacist", "admin"}


def require_role(role: str):
    """Decorator to require a specific role."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") != role:
                flash(f"Please sign in as a {role} to continue.", "error")
                return redirect(url_for("auth.login", role=role))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def require_any_role(*roles: str):
    """Decorator to require any of the specified roles."""
    for role in roles:
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                roles_str = " or ".join(roles)
                flash(f"Please sign in as a {roles_str} to continue.", "error")
                return redirect(url_for("home"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def require_admin():
    """Decorator to require admin role."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") != "admin":
                flash("Admin access required.", "error")
                return redirect(url_for("auth.login", role="admin"))
            return view(*args, **kwargs)
        return wrapped
    return decorator