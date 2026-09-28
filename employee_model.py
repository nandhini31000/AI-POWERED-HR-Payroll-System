"""
app/models/employee_model.py
-------------------------------
Employee model.

NOTE: This is intentionally minimal for Module 1 (Auth). It contains just
enough fields to support login + the dashboards. The FULL set of fields
(Department FK, designation, joining date, bank details, photo, status,
etc.) will be added in the "Employee Module" step, per the development
plan, so we don't dump the whole schema before it's explained.
"""

from datetime import date, datetime
from app import db


class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(20), unique=True, nullable=False)  # e.g. EMP0001
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    joining_date = db.Column(db.Date, default=date.today)
    designation = db.Column(db.String(100), nullable=True)
    employment_type = db.Column(db.String(30), default="Full-time")
    status = db.Column(db.String(30), default="Active")
    address = db.Column(db.Text, nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(60), nullable=True)
    ifsc_code = db.Column(db.String(30), nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One-to-one back-reference to the login account
    user_account = db.relationship("User", backref="employee", uselist=False)
    manager = db.relationship("Employee", remote_side=[id], backref="team_members")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Employee {self.employee_code} - {self.full_name}>"
