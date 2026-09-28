from datetime import date, datetime

from app import db


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    head_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employees = db.relationship("Employee", foreign_keys="Employee.department_id", backref="department", lazy=True)
    head = db.relationship("Employee", foreign_keys=[head_id], post_update=True)


class Attendance(db.Model):
    __tablename__ = "attendance"
    __table_args__ = (db.UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_date"),)

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), nullable=False, default="Present")
    check_in = db.Column(db.Time, nullable=True)
    check_out = db.Column(db.Time, nullable=True)
    overtime_hours = db.Column(db.Numeric(6, 2), default=0)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship("Employee", backref="attendance_records")


class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    leave_type = db.Column(db.String(40), nullable=False, default="Casual")
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days = db.Column(db.Numeric(6, 2), default=1)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="Pending")
    approver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    decision_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    decided_at = db.Column(db.DateTime, nullable=True)

    employee = db.relationship("Employee", backref="leave_requests")
    approver = db.relationship("User")


class LeaveBalance(db.Model):
    __tablename__ = "leave_balances"
    __table_args__ = (db.UniqueConstraint("employee_id", "leave_type", name="uq_leave_balance_employee_type"),)

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    leave_type = db.Column(db.String(40), nullable=False)
    allocated = db.Column(db.Numeric(6, 2), default=12)
    used = db.Column(db.Numeric(6, 2), default=0)

    employee = db.relationship("Employee", backref="leave_balances")

    @property
    def remaining(self):
        return float(self.allocated or 0) - float(self.used or 0)


class SalaryStructure(db.Model):
    __tablename__ = "salary_structures"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), unique=True, nullable=False)
    basic_salary = db.Column(db.Numeric(12, 2), default=0)
    hra = db.Column(db.Numeric(12, 2), default=0)
    da = db.Column(db.Numeric(12, 2), default=0)
    bonus = db.Column(db.Numeric(12, 2), default=0)
    incentives = db.Column(db.Numeric(12, 2), default=0)
    pf = db.Column(db.Numeric(12, 2), default=0)
    professional_tax = db.Column(db.Numeric(12, 2), default=0)
    income_tax = db.Column(db.Numeric(12, 2), default=0)
    leave_deduction_per_day = db.Column(db.Numeric(12, 2), default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship("Employee", backref=db.backref("salary_structure", uselist=False))

    @property
    def gross_salary(self):
        return sum(float(v or 0) for v in [self.basic_salary, self.hra, self.da, self.bonus, self.incentives])

    @property
    def fixed_deductions(self):
        return sum(float(v or 0) for v in [self.pf, self.professional_tax, self.income_tax])


class Payroll(db.Model):
    __tablename__ = "payrolls"
    __table_args__ = (db.UniqueConstraint("employee_id", "month", "year", name="uq_payroll_employee_month"),)

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    present_days = db.Column(db.Numeric(6, 2), default=0)
    absent_days = db.Column(db.Numeric(6, 2), default=0)
    leave_days = db.Column(db.Numeric(6, 2), default=0)
    overtime_hours = db.Column(db.Numeric(6, 2), default=0)
    gross_salary = db.Column(db.Numeric(12, 2), default=0)
    total_deductions = db.Column(db.Numeric(12, 2), default=0)
    net_salary = db.Column(db.Numeric(12, 2), default=0)
    status = db.Column(db.String(20), default="Generated")
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship("Employee", backref="payrolls")


class Payslip(db.Model):
    __tablename__ = "payslips"

    id = db.Column(db.Integer, primary_key=True)
    payroll_id = db.Column(db.Integer, db.ForeignKey("payrolls.id"), unique=True, nullable=False)
    pdf_filename = db.Column(db.String(255), nullable=True)
    qr_payload = db.Column(db.String(255), nullable=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    payroll = db.relationship("Payroll", backref=db.backref("payslip", uselist=False))


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(40), default="info")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(160), nullable=False)
    module = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AIChatLog(db.Model):
    __tablename__ = "ai_chat_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    tool_used = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
