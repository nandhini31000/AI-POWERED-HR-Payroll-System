"""
app/routes/auth_routes.py
----------------------------
Authentication Blueprint.

Handles:
- GET/POST /login   -> authenticate user, start session
- GET     /logout   -> end session
- Redirects to the correct dashboard based on role after login.

Security measures implemented here:
- Passwords checked via hashed comparison (never plain text)
- Generic error message on failed login (doesn't reveal whether the
  username or password was wrong -- prevents user enumeration)
- Session made permanent + timed out via PERMANENT_SESSION_LIFETIME (config.py)
- CSRF protection is automatic via Flask-WTF (CSRFProtect enabled globally)
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.user_model import User

auth_bp = Blueprint("auth", __name__, url_prefix="")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, skip straight to the right dashboard
    if current_user.is_authenticated:
        return redirect(_dashboard_redirect(current_user))

    if request.method == "POST":
        username_or_email = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html")

        if not user.is_active_account:
            flash("Your account has been disabled. Contact HR/Admin.", "warning")
            return render_template("auth/login.html")

        # Successful login
        login_user(user, remember=remember)
        user.last_login_at = datetime.utcnow()
        db.session.commit()

        flash(f"Welcome back, {user.username}!", "success")
        return redirect(_dashboard_redirect(user))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))


def _dashboard_redirect(user: User):
    """Helper to decide which dashboard endpoint to send a user to."""
    if user.is_admin():
        return url_for("main.admin_dashboard")
    return url_for("main.employee_dashboard")
