"""Shared pytest fixtures. Every test gets a fresh in-memory database."""
import os
import sys

import pytest

# Make `import app` work when pytest is run from the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from models import db  # noqa: E402

USER = {
    "full_name": "Test User",
    "email": "test@example.com",
    "password": "secret123",
    "confirm_password": "secret123",
}
admin_user = {
    "full_name": "Admin User",  
    "email": "ezev8915@gmail.com",
    "password": "admin123",
    "confirm_password": "admin123",
}

@pytest.fixture
def app():
    """A Flask app bound to an in-memory SQLite database."""
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """An anonymous test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A test client that has registered and logged in."""
    register(client)
    login(client)
    return client


def register(client, **overrides):
    """POST the registration form with sensible defaults."""
    return client.post("/register", data={**USER, **overrides}, follow_redirects=True)


def login(client, email=USER["email"], passwrd=USER["password"]):
    """POST the login form."""
    return client.post(
        "/login", data={"email": email, ("password"): passwrd}, follow_redirects=True
    )
