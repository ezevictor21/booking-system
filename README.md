# DEZE Travel & Prayer Platform

A faith-based travel website built with **Python (Flask)** and **SQLite**. Visitors can
book journeys, submit prayer requests and contact messages; registered users can record
payments and see their bookings in one place.

The first version of this project was static HTML. This version keeps the same design
and adds a Python backend: every form now posts to a Flask route that validates the
input, saves it to a database and shows a confirmation.

## Features

- Register and log in (passwords hashed with bcrypt, sessions with HttpOnly cookies)
- Booking form saved to the database and linked to the user when logged in
- Prayer request and contact forms saved to the database
- Payment form that records a reference and amount (card details are never collected;
  the next step is redirecting to a hosted provider such as Paystack or Flutterwave)
- "My Account" page listing the user's bookings and payments
- Owner-only admin page for reading bookings, prayer requests and contact messages
- Server-side validation for every form with friendly error messages
- Friendly 404 and 500 pages
- 18 pytest tests

## Project structure

```
deze/
├── app.py              # Flask app, routes, application factory
├── config.py           # Config and TestConfig
├── models.py           # User, Booking, PrayerRequest, ContactMessage, Payment
├── validators.py       # Server-side validation for the six forms
├── requirements.txt
├── Procfile            # gunicorn start command for Render
├── static/style.css
├── templates/          # base.html plus one template per page
└── tests/
    ├── conftest.py
    └── test_app.py
```

## Setup

```bash
git clone https://github.com/ezevictor21/deze.git
cd deze
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. The SQLite database `deze.db` is created on first run.
Set `ADMIN_EMAIL` to the email address of the registered owner account before starting
the app. Only that account can open <http://127.0.0.1:5000/admin>.

In PowerShell, for example:

```powershell
$env:ADMIN_EMAIL = "owner@example.com"
python app.py
```

## Running the tests

```bash
pytest tests/
```

## Routes

| Route | Method | Purpose |
|---|---|---|
| `/` `/about` `/gallery` `/testimonials` | GET | Static pages |
| `/register` `/login` | GET, POST | Accounts |
| `/logout` | POST | End the session |
| `/account` | GET | Logged-in user's bookings and payments |
| `/admin` | GET | Owner-only view of bookings, prayer requests and contact messages |
| `/booking` | GET, POST | Booking form |
| `/prayer` | GET, POST | Prayer request form |
| `/contact` | GET, POST | Contact form |
| `/payment` | GET, POST | Payment intent (login required) |
| `/payment/<reference>` | GET | Confirmation for one payment |

## Next steps

- Connect `/payment` to a hosted checkout and update the status from the provider's callback.
- Send an email confirmation after a booking.
