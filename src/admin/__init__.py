"""Admin blueprint."""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

from src.admin import routes  # noqa: F401, E402