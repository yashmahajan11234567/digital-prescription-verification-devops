"""Admin blueprint package."""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

from src.admin import routes  # noqa: E402