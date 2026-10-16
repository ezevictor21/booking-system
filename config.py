"""Configuration classes for the DEZE Flask application."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_ADMIN_EMAIL = "ezev6145@gmail.com"  # default local admin account

class Config:
    """Default settings. Values come from environment variables when deployed."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "deze.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = bool(os.environ.get("RENDER"))
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).strip()


class TestConfig(Config):
    """Settings used by the test suite: in-memory database, plain cookies."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SESSION_COOKIE_SECURE = False
