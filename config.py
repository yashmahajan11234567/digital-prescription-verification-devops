"""Configuration classes for RxVerify."""
from __future__ import annotations

import os
from pathlib import Path


class BaseConfig:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "local-development-only-change-me")
    TESTING = os.environ.get("TESTING", "0") == "1"
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    FLASK_ENV = "development"
    # Default to SQLite for local development
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///instance/prescriptions.db")


class TestingConfig(BaseConfig):
    """Testing configuration."""
    FLASK_ENV = "testing"
    TESTING = True
    SECRET_KEY = "test-secret-key"
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///:memory:")


class ProductionConfig(BaseConfig):
    """Production configuration (Docker with PostgreSQL)."""
    FLASK_ENV = "production"
    FLASK_DEBUG = False
    DATABASE_URL = os.environ.get("DATABASE_URL")
    SECRET_KEY = os.environ.get("SECRET_KEY")

    def __init__(self):
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL must be set in production")
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in production")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config() -> type[BaseConfig]:
    """Get configuration class based on FLASK_ENV."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, config_by_name["default"])