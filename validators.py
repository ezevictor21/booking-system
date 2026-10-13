"""Server-side validation for every form on the site.

Each function takes the raw form (request.form) and returns (data, errors).
`data` holds cleaned values; `errors` is a list of messages to flash.
The browser's `required` attribute is a convenience only; these checks are
the real rules.
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from models import SERVICES

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN = 6


def _text(form, key):
    """Return a stripped string from the form (empty string if missing)."""
    return (form.get(key) or "").strip()


def _require(value, label, errors, limit=None):
    """Add an error if `value` is empty or longer than `limit`."""
    if not value:
        errors.append(f"{label} is required.")
    elif limit and len(value) > limit:
        errors.append(f"{label} must be {limit} characters or fewer.")


def _email(value, errors, required=True):
    """Add an error if the email is missing (when required) or malformed."""
    if not value:
        if required:
            errors.append("Email is required.")
    elif not EMAIL_RE.match(value):
        errors.append("Enter a valid email address.")


def validate_registration(form):
    """Rules for /register."""
    errors = []
    data = {
        "full_name": _text(form, "full_name"),
        "email": _text(form, "email").lower(),
        "password": form.get("password") or "",
    }
    confirm = form.get("confirm_password") or ""

    _require(data["full_name"], "Full name", errors, 100)
    _email(data["email"], errors)
    if len(data["password"]) < PASSWORD_MIN:
        errors.append(f"Password must be at least {PASSWORD_MIN} characters.")
    elif data["password"] != confirm:
        errors.append("Passwords do not match.")
    return data, errors


def validate_login(form):
    """Rules for /login."""
    errors = []
    data = {
        "email": _text(form, "email").lower(),
        "password": form.get("password") or "",
    }
    _email(data["email"], errors)
    if not data["password"]:
        errors.append("Password is required.")
    return data, errors


def validate_booking(form):
    """Rules for /booking."""
    errors = []
    data = {
        "full_name": _text(form, "full_name"),
        "email": _text(form, "email_address").lower(),
        "phone": _text(form, "phone_number"),
        "service": _text(form, "booking_option"),
        "notes": _text(form, "additional_information"),
    }
    _require(data["full_name"], "Full name", errors, 100)
    _email(data["email"], errors)
    if len(data["phone"]) > 30:
        errors.append("Phone number must be 30 characters or fewer.")
    if data["service"] not in SERVICES:
        errors.append("Please select a service.")
    if len(data["notes"]) > 500:
        errors.append("Additional information must be 500 characters or fewer.")

    raw_date = _text(form, "travel_date")
    try:
        travel_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        travel_date = None
        errors.append("Enter a travel date in the format YYYY-MM-DD.")
    if travel_date and travel_date < date.today():
        errors.append("Travel date cannot be in the past.")
    data["travel_date"] = travel_date
    return data, errors


def validate_prayer(form):
    """Rules for /prayer."""
    errors = []
    data = {
        "name": _text(form, "your_name"),
        "email": _text(form, "email").lower(),
        "request": _text(form, "write_your_prayer_request"),
    }
    _require(data["name"], "Your name", errors, 100)
    _email(data["email"], errors, required=False)
    _require(data["request"], "Prayer request", errors, 1000)
    return data, errors


def validate_contact(form):
    """Rules for /contact."""
    errors = []
    data = {
        "name": _text(form, "your_name"),
        "email": _text(form, "your_email").lower(),
        "message": _text(form, "your_message"),
    }
    _require(data["name"], "Your name", errors, 100)
    _email(data["email"], errors)
    _require(data["message"], "Message", errors, 1000)
    return data, errors


def validate_payment(form):
    """Rules for /payment. Only name, email and amount: never card details."""
    errors = []
    data = {
        "full_name": _text(form, "full_name"),
        "email": _text(form, "email").lower(),
        "amount": None,
    }
    _require(data["full_name"], "Full name", errors, 100)
    _email(data["email"], errors)
    try:
        amount = Decimal(_text(form, "amount"))
        if amount <= 0 or amount > Decimal("100000"):
            raise InvalidOperation
        data["amount"] = amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        errors.append("Enter an amount between 1 and 100000.")
    return data, errors
