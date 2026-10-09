"""Pharmacist blueprint."""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("pharmacist", __name__)

from src.pharmacist import routes  # noqa: F401, E402