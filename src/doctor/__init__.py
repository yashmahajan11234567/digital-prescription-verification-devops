"""Doctor blueprint."""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("doctor", __name__)

from src.doctor import routes  # noqa: F401, E402