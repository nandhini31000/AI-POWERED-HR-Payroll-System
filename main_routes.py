"""
app/routes/main_routes.py
----------------------------
Core navigation routes: "/" and the two role-based dashboards.

This blueprint will stay intentionally thin -- each future module
(Employees, Departments, Attendance, Leave, Payroll, Reports, AI Chat)
gets its OWN blueprint file in app/routes/, registered in app/__init__.py.
That keeps routes.py files small and easy to review one module at a time.
"""

from datetime import date

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import extract, func

from app import db
from app.models.employee_model import Employee
from app.models.hr_models import Attendance, Department, LeaveBalance, LeaveRequest, Payroll
from app.utils.decorators import admin_required, employee_required

main_bp = Blueprint("main", __name__, url_prefix="")


@main_bp.route("/")
def index():
    """Landing route -- sends users to login or their dashboard."""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for("main.admin_dashboard"))
        return redirect(url_for("main.employee_dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """
    Admin Dashboard.
    Placeholder stats for now -- real numbers (Total Employees, Monthly
    Payroll, Pending Leaves, etc.) get wired up once the Employee,
    Payroll, and Leave modules exist and have real tables to query.
    """
    today = date.today()
    monthly_payroll = (
        db.session.query(func.sum(Payroll.net_salary))
        .filter(Payroll.month == today.month, Payroll.year == today.year)
        .scalar()
        or 0
    )
    stats = {
        "total_employees": Employee.query.filter_by(status="Active").count(),
        "departments": Department.query.count(),
        "monthly_payroll": round(float(monthly_payroll), 2),
        "pending_leaves": LeaveRequest.query.filter_by(status="Pending").count(),
    }
    attendance_summary = {
        status: Attendance.query.filter(
            Attendance.attendance_date == today,
            Attendance.status == status,
        ).count()
        for status in ["Present", "Absent", "Late", "Half Day"]
    }
    salary_rows = (
        db.session.query(Payroll.month, func.sum(Payroll.net_salary))
        .filter(Payroll.year == today.year)
        .group_by(Payroll.month)
        .order_by(Payroll.month)
        .all()
    )
    department_rows = (
        db.session.query(Department.name, func.count(Employee.id))
        .outerjoin(Employee, Employee.department_id == Department.id)
        .group_by(Department.id)
        .order_by(Department.name)
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_employees=Employee.query.order_by(Employee.created_at.desc()).limit(5).all(),
        recent_leaves=LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).limit(5).all(),
        attendance_summary=attendance_summary,
        salary_chart={
            "labels": [str(row[0]) for row in salary_rows],
            "values": [round(float(row[1] or 0), 2) for row in salary_rows],
        },
        department_chart={
            "labels": [row[0] for row in department_rows],
            "values": [int(row[1] or 0) for row in department_rows],
        },
    )


@main_bp.route("/employee/dashboard")
@employee_required
def employee_dashboard():
    """
    Employee Dashboard.
    Profile/Salary/Attendance/Leave cards will be populated once those
    modules are built. For now it renders with the logged-in user's
    basic info to prove auth + role routing works end-to-end.
    """
    employee = current_user.employee
    today = date.today()
    latest_payroll = None
    attendance_summary = {}
    leave_balances = []
    recent_leaves = []
    if employee:
        latest_payroll = (
            Payroll.query.filter_by(employee_id=employee.id)
            .order_by(Payroll.year.desc(), Payroll.month.desc())
            .first()
        )
        attendance_summary = {
            status: Attendance.query.filter(
                Attendance.employee_id == employee.id,
                extract("month", Attendance.attendance_date) == today.month,
                extract("year", Attendance.attendance_date) == today.year,
                Attendance.status == status,
            ).count()
            for status in ["Present", "Absent", "Late", "Half Day"]
        }
        leave_balances = LeaveBalance.query.filter_by(employee_id=employee.id).all()
        recent_leaves = (
            LeaveRequest.query.filter_by(employee_id=employee.id)
            .order_by(LeaveRequest.created_at.desc())
            .limit(5)
            .all()
        )
    return render_template(
        "employee/dashboard.html",
        employee=employee,
        latest_payroll=latest_payroll,
        attendance_summary=attendance_summary,
        leave_balances=leave_balances,
        recent_leaves=recent_leaves,
    )
