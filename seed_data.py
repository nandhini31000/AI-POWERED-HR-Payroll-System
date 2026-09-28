"""
seed_data.py
-------------
Creates all database tables and inserts minimal demo data so the app
is usable immediately after setup (Module 1: one admin + one employee
login). Full sample data (20 employees, 5 departments, 6 months
attendance, payroll history, etc.) will be added by seed scripts in
later modules once those tables exist.

Run:
    python seed_data.py
"""

from app import create_app, db
from app.db_utils import assert_database_ready, synchronize_existing_schema
from app.models.user_model import User
from app.models.employee_model import Employee
from app.models.hr_models import LeaveBalance, SalaryStructure

app = create_app()

with app.app_context():
    try:
        db_info = assert_database_ready(app)
        print(f"Database connection OK: {db_info['masked_uri']}")
        if db_info.get("created_database"):
            print(f"Created missing MySQL database: {db_info['database']}")
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(1) from exc

    print("Creating tables (if they don't exist)...")
    db.create_all()
    schema_changes = synchronize_existing_schema(app)
    if schema_changes:
        print("Updated existing schema columns: " + ", ".join(schema_changes))

    # ---------------- Admin account ----------------
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            email="admin@company.com",
            role="admin",
        )
        admin.set_password("Admin@123")
        db.session.add(admin)
        print("Created admin user -> username: admin / password: Admin@123")
    else:
        print("Admin user already exists, skipping.")

    # ---------------- Demo employee + linked user ----------------
    if not Employee.query.filter_by(employee_code="EMP0001").first():
        demo_emp = Employee(
            employee_code="EMP0001",
            first_name="John",
            last_name="Doe",
            email="jdoe@company.com",
        )
        db.session.add(demo_emp)
        db.session.flush()  # get demo_emp.id before commit

        emp_user = User(
            username="jdoe",
            email="jdoe@company.com",
            role="employee",
            employee_id=demo_emp.id,
        )
        emp_user.set_password("Employee@123")
        db.session.add(emp_user)
        print("Created employee user -> username: jdoe / password: Employee@123")
    else:
        print("Demo employee already exists, skipping.")

    for employee in Employee.query.all():
        if not employee.salary_structure:
            db.session.add(SalaryStructure(employee_id=employee.id, basic_salary=25000, hra=10000, da=3000, pf=1800))
        for leave_type in ["Casual", "Sick", "Earned"]:
            if not LeaveBalance.query.filter_by(employee_id=employee.id, leave_type=leave_type).first():
                db.session.add(LeaveBalance(employee_id=employee.id, leave_type=leave_type, allocated=12))

    db.session.commit()
    print("Seeding complete.")
