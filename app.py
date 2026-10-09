"""RxVerify - backward compatibility wrapper for existing imports.

This module preserves the original app.py API while delegating to the new
src package implementation.
"""
from __future__ import annotations

from src import create_app

# Re-export for backward compatibility
__all__ = ["create_app"]

# Create default app instance
app = create_app()