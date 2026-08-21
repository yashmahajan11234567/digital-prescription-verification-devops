"""Authentication blueprint."""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("auth", __name__)

from src.auth import routes  # noqa: F401