"""Tests for the DEZE Flask application. Run with `pytest tests/`."""
from datetime import date, timedelta

from models import Booking, ContactMessage, Payment, PrayerRequest, User

from .conftest import USER, login, register

TOMORROW = (date.today() + timedelta(days=1)).isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()

BOOKING = {
    "full_name": "Test User",
    "email_address": "test@example.com",
    "phone_number": "+44 1234 567890",
    "booking_option": "Pilgrimage Tour",
    "travel_date": TOMORROW,
    "additional_information": "Window seat please",
}


# ---------- pages ----------

# Every public page should load.
def test_public_pages_load(client):
    for path in ("/", "/about", "/gallery", "/testimonials", "/booking",
                 "/prayer", "/contact", "/login", "/register"):
        assert client.get(path).status_code == 200, path


# Unknown URLs show the friendly 404 page.
def test_404_page(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert b"Page not found" in response.data


# ---------- accounts ----------

# Valid registration creates a user with a hashed password.
def test_register_valid(client):
    response = register(client)
    assert response.status_code == 200
    user = User.query.filter_by(email=USER["email"]).first()
    assert user is not None
    assert user.password_hash != USER["password"]
    assert user.check_password(USER["password"])


# Bad email, short password and mismatched confirmation are all rejected.
def test_register_invalid(client):
    assert register(client, email="not-an-email").status_code == 400
    assert register(client, **{("password"): "abc"}, **{("confirm_password"): "abc"}).status_code == 400
    assert register(client, confirm_password="different").status_code == 400
    assert User.query.count() == 0


# The same email cannot register twice.
def test_register_duplicate(client):
    register(client)
    response = register(client)
    assert response.status_code == 400
    assert b"already exists" in response.data
    assert User.query.count() == 1


# Correct credentials log in and reach the account page.
def test_login_success(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    assert b"Welcome, Test User" in response.data


# Wrong password returns 401 and no session.
def test_login_failure(client):
    register(client)
    response = client.post("/login", data={"email": USER["email"], "password": "wrong"})
    assert response.status_code == 401
    assert client.get("/account").status_code == 302


# Account and payment pages need a login; logout clears the session.
def test_protected_routes(auth_client):
    assert auth_client.get("/account").status_code == 200
    assert auth_client.get("/payment").status_code == 200
    auth_client.post("/logout")
    assert auth_client.get("/account").status_code == 302
    assert auth_client.get("/payment").status_code == 302


# ---------- forms ----------

# A booking is saved and linked to the logged-in user.
def test_booking_saved(auth_client):
    response = auth_client.post("/booking", data=BOOKING, follow_redirects=True)
    assert response.status_code == 200
    assert b"booking for" in response.data
    booking = Booking.query.one()
    assert booking.service == "Pilgrimage Tour"
    assert booking.user.email == USER["email"]
    assert booking.travel_date.isoformat() == TOMORROW


# A visitor who is not logged in can still book.
def test_booking_anonymous(client):
    response = client.post("/booking", data=BOOKING)
    assert response.status_code == 302
    assert Booking.query.one().user_id is None


# Past dates, bad dates, unknown services and missing names are rejected.
def test_booking_invalid(client):
    assert client.post("/booking", data={**BOOKING, "travel_date": YESTERDAY}).status_code == 400
    assert client.post("/booking", data={**BOOKING, "travel_date": "31/12/2026"}).status_code == 400
    assert client.post("/booking", data={**BOOKING, "booking_option": "Cruise"}).status_code == 400
    assert client.post("/booking", data={**BOOKING, "full_name": ""}).status_code == 400
    assert Booking.query.count() == 0


# Prayer requests save without an email, but not without text.
def test_prayer_request(client):
    ok = client.post("/prayer", data={"your_name": "Ada", "write_your_prayer_request": "Peace"})
    assert ok.status_code == 302
    bad = client.post("/prayer", data={"your_name": "Ada", "write_your_prayer_request": ""})
    assert bad.status_code == 400
    assert PrayerRequest.query.count() == 1


# Contact messages need name, valid email and message.
def test_contact_message(client):
    data = {"your_name": "Ada", "your_email": "ada@example.com", "your_message": "Hello"}
    assert client.post("/contact", data=data).status_code == 302
    assert client.post("/contact", data={**data, "your_email": "nope"}).status_code == 400
    assert ContactMessage.query.count() == 1


# A payment records a reference and amount; the status page shows it.
def test_payment_recorded(auth_client):
    response = auth_client.post(
        "/payment",
        data={"full_name": "Test User", "email": USER["email"], "amount": "150"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    payment = Payment.query.one()
    assert payment.reference.startswith("DEZE-")
    assert str(payment.amount) == "150.00"
    assert payment.reference.encode() in response.data


# Zero, negative and non-numeric amounts are rejected.
def test_payment_invalid_amount(auth_client):
    for amount in ("0", "-5", "abc", ""):
        response = auth_client.post(
            "/payment", data={"full_name": "Test User", "email": USER["email"], "amount": amount}
        )
        assert response.status_code == 400, amount
    assert Payment.query.count() == 0


# One user cannot see another user's payment reference.
def test_payment_ownership(client):
    register(client)
    login(client)
    client.post("/payment", data={"full_name": "Test User", "email": USER["email"], "amount": "20"})
    reference = Payment.query.one().reference
    client.post("/logout")

    register(client, email="other@example.com")
    login(client, email="other@example.com")
    assert client.get(f"/payment/{reference}").status_code == 404


# Only the configured owner can read submissions.
def test_admin_requires_owner(client, auth_client):
    anonymous_client = client.application.test_client()
    assert anonymous_client.get("/admin").status_code == 302

    auth_client.application.config["ADMIN_EMAIL"] = "owner@example.com"
    assert auth_client.get("/admin").status_code == 403


# The owner dashboard displays all three types of submitted form.
def test_admin_lists_submissions(client):
    client.application.config["ADMIN_EMAIL"] = "owner@example.com"
    register(client, email="owner@example.com")
    login(client, email="owner@example.com")

    client.post("/booking", data=BOOKING)
    client.post(
        "/prayer",
        data={"your_name": "Prayer Person", "email": "prayer@example.com",
              "write_your_prayer_request": "Please pray for peace"},
    )
    client.post(
        "/contact",
        data={"your_name": "Message Person", "your_email": "message@example.com",
              "your_message": "I would like more information"},
    )

    response = client.get("/admin")
    assert response.status_code == 200
    assert b"Test User" in response.data
    assert b"Pilgrimage Tour" in response.data
    assert b"Please pray for peace" in response.data
    assert b"I would like more information" in response.data
