"""DEZE Travel & Prayer Platform - Flask application.

Run locally with `python app.py`. The static HTML pages from the first
version of the site now live in `templates/` and are served by the routes
below. Every form posts to a route that validates the input, saves it to
SQLite and shows a confirmation message.
"""
import os
import secrets
from functools import wraps
ADMIN_EMAIL = "ezev6145@gmail.com"  # ✅ Your admin email
try:
    import resend
except ImportError:  # pragma: no cover - optional mail dependency
    resend = None

if resend is not None:
    resend.api_key = os.environ.get("RESEND_API_KEY")


from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from config import Config
from models import (
    SERVICES,
    Booking,
    ContactMessage,
    Payment,
    PrayerRequest,
    User,
    bcrypt,
    db,
)
from validators import (
    validate_booking,
    validate_contact,
    validate_login,
    validate_payment,
    validate_prayer,
    validate_registration,
)


def login_required(view):
    """Redirect to the login page when no user is in the session."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def current_user():
    """Return the logged-in User, or None."""
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def flash_errors(errors):
    """Flash each validation message so the template can show it."""
    for message in errors:
        flash(message, "error")


def save(obj):
    """Add an object to the session and commit. Return True on success."""
    try:
        db.session.add(obj)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        flash("Something went wrong while saving. Please try again.", "error")
        return False


def create_app(config_object=Config):
    """Application factory. Tests pass TestConfig for an in-memory database."""
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.config.setdefault("ADMIN_EMAIL", getattr(config_object, "ADMIN_EMAIL", "").strip() or "ezev6145@gmail.com")

    db.init_app(app)
    bcrypt.init_app(app)

    @app.context_processor
    def inject_globals():
        """Make the current user and service list available in every template."""
        user = current_user()
        admin_email = (app.config.get("ADMIN_EMAIL") or "").strip().casefold()
        is_admin = bool(admin_email and user and user.email.casefold() == admin_email)
        return {
            "current_user": user,
            "services": SERVICES,
            "is_admin": is_admin,
        }

    register_routes(app)
    register_error_handlers(app)

    with app.app_context():
        db.create_all()

    return app


def register_error_handlers(app):
    """Friendly 404 and 500 pages."""

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="Page not found"), 404

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403, message="You are not authorized to view this page"), 403

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("error.html", code=500, message="Something went wrong"), 500


def register_routes(app):
    """Attach every route to the app."""

    # ---------- static pages ----------

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/gallery")
    def gallery():
        return render_template("gallery.html")

    @app.route("/testimonials")
    def testimonials():
        return render_template("testimonials.html")

    # ---------- accounts ----------

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            data, errors = validate_registration(request.form)
            if not errors and User.query.filter_by(email=data["email"]).first():
                errors.append("An account with that email already exists.")
            if errors:
                flash_errors(errors)
                return render_template("register.html", form=request.form), 400

            user = User(full_name=data["full_name"], email=data["email"])
            user.set_password(data["password"])
            if save(user):
                flash("Account created. You can log in now.", "success")
                return redirect(url_for("login"))
        return render_template("register.html", form={})

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            data, errors = validate_login(request.form)
            user = None
            if not errors:
                user = User.query.filter_by(email=data["email"]).first()
                if not user or not user.check_password(data["password"]):
                    errors.append("Invalid email or password.")
            if errors:
                flash_errors(errors)
                return render_template("login.html", form=request.form), 401

            session.clear()  # prevent session fixation
            session["user_id"] = user.id
            flash(f"Welcome back, {user.full_name}.", "success")
            next_page = request.args.get("next", "")
            if next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for("account"))
        return render_template("login.html", form={})

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("index"))

    @app.route("/account")
    @login_required
    def account():
        """The logged-in user's bookings and payments."""
        user = current_user()
        bookings = (
            Booking.query.filter_by(user_id=user.id)
            .order_by(Booking.travel_date)
            .all()
        )
        payments = (
            Payment.query.filter_by(user_id=user.id)
            .order_by(Payment.created_at.desc())
            .all()
        )
        return render_template("account.html", bookings=bookings, payments=payments)

    @app.route("/admin")
    @login_required
    def admin():
        """Show submitted bookings, prayer requests and contact messages to the owner."""
        user = current_user()
        admin_email = (app.config.get("ADMIN_EMAIL") or "").strip().casefold()
        if not admin_email or user is None or user.email.casefold() != admin_email:
            abort(403)

        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        prayer_requests = PrayerRequest.query.order_by(PrayerRequest.created_at.desc()).all()
        messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
        return render_template(
            "admin.html",
            bookings=bookings,
            prayer_requests=prayer_requests,
            messages=messages,
        )

    # ---------- the six forms ----------

    @app.route("/booking", methods=["GET", "POST"])
    def booking():
        if request.method == "POST":
            data, errors = validate_booking(request.form)
            if errors:
                flash_errors(errors)
                return render_template("booking.html", form=request.form), 400

            user = current_user()
            item = Booking(user_id=user.id if user else None, **data)
            if save(item):
                if resend is not None and getattr(resend, "api_key", None):
                    try:
                        resend.emails.send({
                            "from": "onboarding@resend.dev",
                            "to": "ezevictor6145@gmail.com",
                            "subject": "📩 New Booking Received!",
                            "html": f"""
                            <h3>New Booking from Your Website</h3>
                            <p><strong>Name:</strong> {data['full_name']}</p>
                            <p><strong>Email:</strong> {data['email']}</p>
                            <p><strong>Phone:</strong> {data['phone']}</p>
                            <p><strong>Service:</strong> {data['service']}</p>
                            <p><strong>Travel Date:</strong> {data['travel_date']}</p>
                            """,
                        })
                    except Exception as e:
                        print(f"Email error: {e}")
                flash(
                    f"Thank you {data['full_name']}, your {data['service']} booking "
                    f"for {data['travel_date']:%d %B %Y} has been received.",
                    "success",
                )
                return redirect(url_for("account" if user else "booking"))
        return render_template("booking.html", form={})
       

    @app.route("/prayer", methods=["GET", "POST"])
    def prayer():
        if request.method == "POST":
            data, errors = validate_prayer(request.form)
            if errors:
                flash_errors(errors)
                return render_template("prayer.html", form=request.form), 400
            if save(PrayerRequest(**data)):
                flash("Your prayer request has been received. We are praying with you.", "success")
                return redirect(url_for("prayer"))
        return render_template("prayer.html", form={})

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            data, errors = validate_contact(request.form)
            if errors:
                flash_errors(errors)
                return render_template("contact.html", form=request.form), 400
            if save(ContactMessage(**data)):
                flash("Message sent. We will reply to you by email.", "success")
                return redirect(url_for("contact"))
        return render_template("contact.html", form={})

    @app.route("/payment", methods=["GET", "POST"])
    @login_required
    def payment():
        """Record a payment intent. Card entry belongs to a hosted provider page,
        so the only thing stored here is who is paying and how much."""
        user = current_user()
        if request.method == "POST":
            data, errors = validate_payment(request.form)
            if errors:
                flash_errors(errors)
                return render_template("payment.html", form=request.form), 400

            item = Payment(
                user_id=user.id,
                reference="DEZE-" + secrets.token_hex(6).upper(),
                **data,
            )
            if save(item):
                return redirect(url_for("payment_status", reference=item.reference))
        prefill = {"full_name": user.full_name, "email": user.email}
        return render_template("payment.html", form=prefill)

    @app.route("/payment/<reference>")
    @login_required
    def payment_status(reference):
        """Confirmation page for one payment. Other users' references are hidden."""
        user = current_user()
        item = Payment.query.filter_by(reference=reference, user_id=user.id).first()
        if item is None:
            abort(404)
        return render_template("payment_status.html", payment=item)
    
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
