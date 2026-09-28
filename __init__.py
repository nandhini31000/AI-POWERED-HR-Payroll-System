"""
app/models/__init__.py
------------------------
Central place to import all models so that `db.create_all()` (run.py)
and Alembic/Flask-Migrate can discover every table.

As we add modules (Department, Attendance, Leave, Payroll, etc.) their
model files will be imported here too.
"""

from app.models.user_model import User
from app.models.employee_model import Employee
from app.models.hr_models import (
    AIChatLog,
    ActivityLog,
    Attendance,
    Department,
    LeaveBalance,
    LeaveRequest,
    Notification,
    Payroll,
    Payslip,
    SalaryStructure,
)

__all__ = [
    "User",
    "Employee",
    "Department",
    "Attendance",
    "LeaveRequest",
    "LeaveBalance",
    "SalaryStructure",
    "Payroll",
    "Payslip",
    "Notification",
    "ActivityLog",
    "AIChatLog",
]
