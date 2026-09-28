"""
app/models/user_model.py
--------------------------
User model used for authentication (Admin + Employee roles).

Design notes:
- Passwords are NEVER stored in plain text. We store only a salted hash
  using Werkzeug's generate_password_hash / check_password_hash.
- `role` is a simple string field ("admin" / "employee") to keep the
  model simple and easy for a student to understand, while still
  supporting Role-Based Access Control (RBAC) via the decorators in
  app/utils/decorators.py.
- Linked 1-to-1 with Employee via employee_id (nullable, because an
  Admin user does not need an employee record).
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # 'admin' or 'employee' -- drives which dashboard/menu is shown
    role = db.Column(db.String(20), nullable=False, default="employee")

    # Link to employee profile (NULL for admin-only accounts)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)

    is_active_account = db.Column(db.Boolean, default=True)  # allow disabling accounts
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship back to Employee (defined with backref in employee_model.py)

    # -------------------------------------------------------------
    # Password helpers
    # -------------------------------------------------------------
    def set_password(self, plain_password: str) -> None:
        """Hash and store the given plain-text password."""
        self.password_hash = generate_password_hash(plain_password)

    def check_password(self, plain_password: str) -> bool:
        """Verify a plain-text password against the stored hash."""
        return check_password_hash(self.password_hash, plain_password)

    # -------------------------------------------------------------
    # Role helpers (used by route guards / templates)
    # -------------------------------------------------------------
    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_employee(self) -> bool:
        return self.role == "employee"

    # Flask-Login requires `is_active` -- we map it to our own column
    @property
    def is_active(self):
        return self.is_active_account

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
