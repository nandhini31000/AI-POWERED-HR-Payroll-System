from calendar import monthrange
from datetime import date, datetime, time
from io import BytesIO
import os

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import extract, func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from app import db
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
from app.models.user_model import User
from app.utils.decorators import admin_required, roles_required
from app.agent.payroll_agent import agent

hr_bp = Blueprint("hr", __name__, url_prefix="")
api_bp = Blueprint("api", __name__, url_prefix="/api")


def log_activity(action, module):
    actor = current_user.username if current_user.is_authenticated else "system"
    db.session.add(ActivityLog(actor=actor, action=action, module=module))


def parse_date(value, default=None):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_time(value):
    if not value:
        return None
    hour, minute = value.split(":")[:2]
    return time(int(hour), int(minute))


def money(value):
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def employee_payload(employee):
    return {
        "id": employee.id,
        "employee_code": employee.employee_code,
        "name": employee.full_name,
        "email": employee.email,
        "phone": employee.phone,
        "department": employee.department.name if employee.department else None,
        "designation": employee.designation,
        "status": employee.status,
    }


def payroll_payload(payroll):
    return {
        "id": payroll.id,
        "employee": payroll.employee.full_name,
        "month": payroll.month,
        "year": payroll.year,
        "gross_salary": money(payroll.gross_salary),
        "total_deductions": money(payroll.total_deductions),
        "net_salary": money(payroll.net_salary),
        "status": payroll.status,
    }


def current_employee():
    return getattr(current_user, "employee", None)


def allowed_photo(filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return extension in current_app.config["ALLOWED_EXTENSIONS"]


def save_employee_photo(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_photo(file_storage.filename):
        flash("Unsupported photo format. Use png, jpg, jpeg, or gif.", "warning")
        return None
    filename = f"{int(datetime.utcnow().timestamp())}_{secure_filename(file_storage.filename)}"
    file_storage.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
    return filename


def generate_employee_code():
    latest = Employee.query.order_by(Employee.id.desc()).first()
    next_id = (latest.id if latest else 0) + 1
    while True:
        code = f"EMP{next_id:04d}"
        if not Employee.query.filter_by(employee_code=code).first():
            return code
        next_id += 1


def upsert_salary(employee, form):
    salary = employee.salary_structure or SalaryStructure(employee_id=employee.id)
    for field in [
        "basic_salary",
        "hra",
        "da",
        "bonus",
        "incentives",
        "pf",
        "professional_tax",
        "income_tax",
        "leave_deduction_per_day",
    ]:
        setattr(salary, field, money(form.get(field)))
    db.session.add(salary)
    return salary


def calculate_payroll(employee, month, year):
    salary = employee.salary_structure
    if not salary:
        salary = SalaryStructure(employee_id=employee.id, basic_salary=25000, hra=10000, da=3000)
        db.session.add(salary)
        db.session.flush()

    records = Attendance.query.filter(
        Attendance.employee_id == employee.id,
        extract("month", Attendance.attendance_date) == month,
        extract("year", Attendance.attendance_date) == year,
    ).all()
    present = sum(1 for item in records if item.status in {"Present", "Late"})
    absent = sum(1 for item in records if item.status == "Absent")
    overtime = sum(money(item.overtime_hours) for item in records)
    approved_leaves = LeaveRequest.query.filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.status == "Approved",
        extract("month", LeaveRequest.start_date) == month,
        extract("year", LeaveRequest.start_date) == year,
    ).all()
    leave_days = sum(money(item.days) for item in approved_leaves)
    leave_deduction = leave_days * money(salary.leave_deduction_per_day)
    overtime_pay = overtime * 150
    gross = money(salary.gross_salary + overtime_pay)
    deductions = money(salary.fixed_deductions + leave_deduction)
    net = money(gross - deductions)

    payroll = Payroll.query.filter_by(employee_id=employee.id, month=month, year=year).first()
    if not payroll:
        payroll = Payroll(employee_id=employee.id, month=month, year=year)

    payroll.present_days = present
    payroll.absent_days = absent
    payroll.leave_days = leave_days
    payroll.overtime_hours = overtime
    payroll.gross_salary = gross
    payroll.total_deductions = deductions
    payroll.net_salary = net
    payroll.status = "Generated"
    payroll.generated_at = datetime.utcnow()
    db.session.add(payroll)
    return payroll


def generate_simple_pdf(title, lines):
    content = ["BT", "/F1 18 Tf", "72 760 Td", f"({title}) Tj", "/F1 10 Tf"]
    y_step = 18
    for line in lines:
        safe = str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content.append(f"0 -{y_step} Td ({safe}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n",
    ]
    pdf = BytesIO()
    pdf.write(b"%PDF-1.4\n")
    offsets = []
    for obj in objects:
        offsets.append(pdf.tell())
        pdf.write(obj)
    xref = pdf.tell()
    pdf.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets:
        pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.write(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode("ascii"))
    pdf.seek(0)
    return pdf


@hr_bp.route("/employees")
@admin_required
def employees():
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    department_id = request.args.get("department_id", type=int)
    page = request.args.get("page", 1, type=int)
    employees_query = Employee.query
    if query:
        like = f"%{query}%"
        employees_query = employees_query.filter(
            or_(
                Employee.first_name.ilike(like),
                Employee.last_name.ilike(like),
                Employee.employee_code.ilike(like),
                Employee.email.ilike(like),
                Employee.designation.ilike(like),
            )
        )
    if status:
        employees_query = employees_query.filter(Employee.status == status)
    if department_id:
        employees_query = employees_query.filter(Employee.department_id == department_id)
    pagination = employees_query.order_by(Employee.employee_code).paginate(page=page, per_page=8, error_out=False)
    return render_template(
        "modules/employees.html",
        pagination=pagination,
        q=query,
        status=status,
        department_id=department_id,
        departments=Department.query.order_by(Department.name).all(),
    )


@hr_bp.route("/employees/new", methods=["GET", "POST"])
@admin_required
def employee_new():
    return employee_form()


@hr_bp.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
@admin_required
def employee_edit(employee_id):
    return employee_form(Employee.query.get_or_404(employee_id))


def employee_form(employee=None):
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        employee = employee or Employee()
        employee.employee_code = request.form.get("employee_code", "").strip() or generate_employee_code()
        employee.first_name = request.form.get("first_name", "").strip()
        employee.last_name = request.form.get("last_name", "").strip()
        employee.email = request.form.get("email", "").strip()
        if not employee.first_name or not employee.last_name or not employee.email:
            flash("First name, last name, and email are required.", "danger")
            return render_template("modules/employee_form.html", employee=employee, departments=departments)
        employee.phone = request.form.get("phone")
        employee.gender = request.form.get("gender")
        employee.date_of_birth = parse_date(request.form.get("date_of_birth"))
        employee.joining_date = parse_date(request.form.get("joining_date"), date.today())
        employee.designation = request.form.get("designation")
        employee.employment_type = request.form.get("employment_type", "Full-time")
        employee.status = request.form.get("status", "Active")
        employee.address = request.form.get("address")
        employee.department_id = request.form.get("department_id", type=int) or None
        employee.bank_name = request.form.get("bank_name")
        employee.bank_account = request.form.get("bank_account")
        employee.ifsc_code = request.form.get("ifsc_code")
        photo = save_employee_photo(request.files.get("photo"))
        if photo:
            employee.photo_filename = photo
        db.session.add(employee)
        db.session.flush()

        username = request.form.get("username", employee.employee_code.lower()).strip()
        password = request.form.get("password", "Employee@123")
        if username and not employee.user_account:
            user = User(username=username, email=employee.email, role="employee", employee_id=employee.id)
            user.set_password(password)
            db.session.add(user)
        elif employee.user_account:
            employee.user_account.email = employee.email
            if password:
                employee.user_account.set_password(password)

        upsert_salary(employee, request.form)
        for leave_type in ["Casual", "Sick", "Earned"]:
            if not LeaveBalance.query.filter_by(employee_id=employee.id, leave_type=leave_type).first():
                db.session.add(LeaveBalance(employee_id=employee.id, leave_type=leave_type, allocated=12))
        log_activity(f"Saved employee {employee.employee_code}", "Employees")
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Employee code, email, or username already exists.", "danger")
            return render_template("modules/employee_form.html", employee=employee, departments=departments)
        flash("Employee saved successfully.", "success")
        return redirect(url_for("hr.employee_profile", employee_id=employee.id))

    return render_template("modules/employee_form.html", employee=employee, departments=departments)


@hr_bp.route("/employees/<int:employee_id>")
@roles_required("admin", "employee")
def employee_profile(employee_id):
    if current_user.is_employee() and (not current_employee() or current_employee().id != employee_id):
        flash("You can only view your own profile.", "danger")
        return redirect(url_for("main.employee_dashboard"))
    employee = Employee.query.get_or_404(employee_id)
    return render_template("modules/employee_profile.html", employee=employee)


@hr_bp.route("/employees/<int:employee_id>/delete", methods=["POST"])
@admin_required
def employee_delete(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    employee.status = "Inactive"
    log_activity(f"Deactivated employee {employee.employee_code}", "Employees")
    db.session.commit()
    flash("Employee deactivated.", "info")
    return redirect(url_for("hr.employees"))


@hr_bp.route("/departments", methods=["GET", "POST"])
@admin_required
def departments():
    if request.method == "POST":
        department = Department(
            name=request.form["name"].strip(),
            code=request.form["code"].strip().upper(),
            description=request.form.get("description"),
            head_id=request.form.get("head_id", type=int) or None,
        )
        db.session.add(department)
        log_activity(f"Created department {department.name}", "Departments")
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Department name or code already exists.", "danger")
            return redirect(url_for("hr.departments"))
        flash("Department created.", "success")
        return redirect(url_for("hr.departments"))
    return render_template(
        "modules/departments.html",
        departments=Department.query.order_by(Department.name).all(),
        employees=Employee.query.order_by(Employee.first_name).all(),
    )


@hr_bp.route("/departments/<int:department_id>/edit", methods=["POST"])
@admin_required
def department_edit(department_id):
    department = Department.query.get_or_404(department_id)
    department.name = request.form["name"].strip()
    department.code = request.form["code"].strip().upper()
    department.description = request.form.get("description")
    department.head_id = request.form.get("head_id", type=int) or None
    log_activity(f"Updated department {department.name}", "Departments")
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Department name or code already exists.", "danger")
        return redirect(url_for("hr.departments"))
    flash("Department updated.", "success")
    return redirect(url_for("hr.departments"))


@hr_bp.route("/departments/assign", methods=["POST"])
@admin_required
def department_assign():
    employee = Employee.query.get_or_404(request.form.get("employee_id", type=int))
    department_id = request.form.get("department_id", type=int)
    employee.department_id = department_id or None
    log_activity(f"Assigned {employee.employee_code} to department", "Departments")
    db.session.commit()
    flash("Employee department assignment updated.", "success")
    return redirect(url_for("hr.departments"))


@hr_bp.route("/departments/<int:department_id>/delete", methods=["POST"])
@admin_required
def department_delete(department_id):
    department = Department.query.get_or_404(department_id)
    if department.employees:
        flash("Move employees out of this department before deleting it.", "warning")
    else:
        db.session.delete(department)
        log_activity(f"Deleted department {department.name}", "Departments")
        db.session.commit()
        flash("Department deleted.", "info")
    return redirect(url_for("hr.departments"))


@hr_bp.route("/attendance", methods=["GET", "POST"])
@admin_required
def attendance():
    selected_date = parse_date(request.values.get("attendance_date"), date.today())
    if request.method == "POST":
        for employee in Employee.query.filter_by(status="Active").all():
            status = request.form.get(f"status_{employee.id}", "Present")
            record = Attendance.query.filter_by(employee_id=employee.id, attendance_date=selected_date).first()
            if not record:
                record = Attendance(employee_id=employee.id, attendance_date=selected_date)
            record.status = status
            record.check_in = parse_time(request.form.get(f"check_in_{employee.id}"))
            record.check_out = parse_time(request.form.get(f"check_out_{employee.id}"))
            record.overtime_hours = money(request.form.get(f"overtime_{employee.id}"))
            record.notes = request.form.get(f"notes_{employee.id}")
            db.session.add(record)
        log_activity(f"Marked attendance for {selected_date}", "Attendance")
        db.session.commit()
        flash("Attendance saved.", "success")
        return redirect(url_for("hr.attendance", attendance_date=selected_date))

    records = {item.employee_id: item for item in Attendance.query.filter_by(attendance_date=selected_date).all()}
    return render_template(
        "modules/attendance.html",
        employees=Employee.query.filter_by(status="Active").order_by(Employee.employee_code).all(),
        records=records,
        selected_date=selected_date,
    )


@hr_bp.route("/attendance/reports")
@roles_required("admin", "employee")
def attendance_reports():
    employee_id = request.args.get("employee_id", type=int)
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    if current_user.is_employee() and current_employee():
        employee_id = current_employee().id
    query = Attendance.query
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    if month:
        query = query.filter(extract("month", Attendance.attendance_date) == month)
    if year:
        query = query.filter(extract("year", Attendance.attendance_date) == year)
    records = query.order_by(Attendance.attendance_date.desc()).limit(300).all()
    summary = {status: sum(1 for item in records if item.status == status) for status in ["Present", "Absent", "Late", "Half Day"]}
    return render_template(
        "modules/attendance_report.html",
        records=records,
        employees=Employee.query.all(),
        employee_id=employee_id,
        month=month,
        year=year,
        summary=summary,
    )


@hr_bp.route("/leaves", methods=["GET", "POST"])
@roles_required("admin", "employee")
def leaves():
    employee = current_employee()
    if request.method == "POST":
        employee_id = request.form.get("employee_id", type=int) if current_user.is_admin() else employee.id
        start = parse_date(request.form["start_date"])
        end = parse_date(request.form["end_date"])
        if end < start:
            flash("Leave end date cannot be before start date.", "danger")
            return redirect(url_for("hr.leaves"))
        days = (end - start).days + 1
        balance = LeaveBalance.query.filter_by(employee_id=employee_id, leave_type=request.form.get("leave_type", "Casual")).first()
        if balance and balance.remaining < days:
            flash("Insufficient leave balance for this request.", "warning")
            return redirect(url_for("hr.leaves"))
        leave = LeaveRequest(
            employee_id=employee_id,
            leave_type=request.form.get("leave_type", "Casual"),
            start_date=start,
            end_date=end,
            days=days,
            reason=request.form.get("reason"),
        )
        db.session.add(leave)
        db.session.add(Notification(title="Pending leave request", message=f"{leave.employee.full_name} requested {days} day(s) of {leave.leave_type} leave.", category="warning"))
        log_activity("Applied leave request", "Leaves")
        db.session.commit()
        flash("Leave request submitted.", "success")
        return redirect(url_for("hr.leaves"))
    query = LeaveRequest.query
    if current_user.is_employee() and employee:
        query = query.filter_by(employee_id=employee.id)
    return render_template(
        "modules/leaves.html",
        leaves=query.order_by(LeaveRequest.created_at.desc()).all(),
        balances=LeaveBalance.query.filter_by(employee_id=employee.id).all() if employee else [],
        employees=Employee.query.filter_by(status="Active").all(),
    )


@hr_bp.route("/leaves/<int:leave_id>/<decision>", methods=["POST"])
@admin_required
def leave_decision(leave_id, decision):
    leave = LeaveRequest.query.get_or_404(leave_id)
    leave.status = "Approved" if decision == "approve" else "Rejected"
    leave.approver_id = current_user.id
    leave.decision_notes = request.form.get("decision_notes")
    leave.decided_at = datetime.utcnow()
    if leave.status == "Approved":
        balance = LeaveBalance.query.filter_by(employee_id=leave.employee_id, leave_type=leave.leave_type).first()
        if balance:
            balance.used = money(balance.used) + money(leave.days)
    db.session.add(Notification(title=f"Leave {leave.status}", message=f"{leave.employee.full_name}'s leave request was {leave.status.lower()}.", category="success" if leave.status == "Approved" else "danger"))
    log_activity(f"{leave.status} leave for {leave.employee.full_name}", "Leaves")
    db.session.commit()
    flash(f"Leave {leave.status.lower()}.", "success")
    return redirect(url_for("hr.leaves"))


@hr_bp.route("/salary", methods=["GET", "POST"])
@admin_required
def salary():
    employees = Employee.query.filter_by(status="Active").order_by(Employee.employee_code).all()
    if request.method == "POST":
        employee = Employee.query.get_or_404(request.form.get("employee_id", type=int))
        upsert_salary(employee, request.form)
        log_activity(f"Updated salary for {employee.employee_code}", "Salary")
        db.session.commit()
        flash("Salary structure saved.", "success")
        return redirect(url_for("hr.salary"))
    return render_template("modules/salary.html", employees=employees)


@hr_bp.route("/payroll", methods=["GET", "POST"])
@admin_required
def payroll():
    today = date.today()
    month = request.values.get("month", today.month, type=int)
    year = request.values.get("year", today.year, type=int)
    if request.method == "POST":
        target_ids = request.form.getlist("employee_ids") or [str(item.id) for item in Employee.query.filter_by(status="Active")]
        for employee_id in target_ids:
            employee = Employee.query.get(int(employee_id))
            if employee:
                calculate_payroll(employee, month, year)
        db.session.add(Notification(title="Payroll generated", message=f"Payroll generated for {month}/{year}.", category="success"))
        log_activity(f"Generated payroll for {month}/{year}", "Payroll")
        db.session.commit()
        flash("Payroll generated.", "success")
        return redirect(url_for("hr.payroll", month=month, year=year))
    payrolls = Payroll.query.filter_by(month=month, year=year).order_by(Payroll.net_salary.desc()).all()
    return render_template("modules/payroll.html", employees=Employee.query.filter_by(status="Active").all(), payrolls=payrolls, month=month, year=year)


@hr_bp.route("/payslips")
@roles_required("admin", "employee")
def payslips():
    query = Payroll.query
    if current_user.is_employee() and current_employee():
        query = query.filter_by(employee_id=current_employee().id)
    return render_template("modules/payslips.html", payrolls=query.order_by(Payroll.year.desc(), Payroll.month.desc()).all())


@hr_bp.route("/payslips/<int:payroll_id>/download")
@roles_required("admin", "employee")
def payslip_download(payroll_id):
    payroll = Payroll.query.get_or_404(payroll_id)
    if current_user.is_employee() and current_employee().id != payroll.employee_id:
        flash("You can only download your own payslip.", "danger")
        return redirect(url_for("hr.payslips"))
    if not payroll.payslip:
        db.session.add(Payslip(payroll_id=payroll.id, qr_payload=f"PAYSLIP-{payroll.id}-{payroll.net_salary}"))
        db.session.commit()
    lines = [
        f"Employee: {payroll.employee.full_name} ({payroll.employee.employee_code})",
        f"Period: {payroll.month}/{payroll.year}",
        f"Gross Salary: Rs. {money(payroll.gross_salary)}",
        f"Deductions: Rs. {money(payroll.total_deductions)}",
        f"Net Salary: Rs. {money(payroll.net_salary)}",
        f"Verification QR Payload: {payroll.payslip.qr_payload}",
    ]
    pdf = generate_simple_pdf("Payslip", lines)
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name=f"payslip_{payroll.id}.pdf")


@hr_bp.route("/reports")
@admin_required
def reports():
    return render_template(
        "modules/reports.html",
        payroll_total=db.session.query(func.sum(Payroll.net_salary)).scalar() or 0,
        department_count=Department.query.count(),
        attendance_count=Attendance.query.count(),
    )


@hr_bp.route("/reports/<report_type>/export.<fmt>")
@admin_required
def report_export(report_type, fmt):
    rows = []
    if report_type == "payroll":
        rows = [["Employee", "Month", "Year", "Gross", "Deductions", "Net"]] + [
            [p.employee.full_name, p.month, p.year, money(p.gross_salary), money(p.total_deductions), money(p.net_salary)]
            for p in Payroll.query.order_by(Payroll.year.desc(), Payroll.month.desc()).all()
        ]
    elif report_type == "attendance":
        rows = [["Employee", "Date", "Status", "Overtime"]] + [
            [a.employee.full_name, a.attendance_date, a.status, money(a.overtime_hours)] for a in Attendance.query.limit(500)
        ]
    elif report_type == "leave":
        rows = [["Employee", "Type", "Start", "End", "Days", "Status"]] + [
            [l.employee.full_name, l.leave_type, l.start_date, l.end_date, money(l.days), l.status]
            for l in LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).limit(500)
        ]
    elif report_type == "employee":
        rows = [["Code", "Name", "Email", "Department", "Designation", "Status"]] + [
            [e.employee_code, e.full_name, e.email, e.department.name if e.department else "", e.designation or "", e.status]
            for e in Employee.query.order_by(Employee.employee_code).all()
        ]
    elif report_type == "department":
        rows = [["Department", "Head", "Employee Count"]] + [
            [d.name, d.head.full_name if d.head else "", len(d.employees)] for d in Department.query.all()
        ]
    else:
        flash("Unknown report type.", "danger")
        return redirect(url_for("hr.reports"))

    if fmt == "pdf":
        lines = [", ".join(map(str, row)) for row in rows]
        return send_file(generate_simple_pdf(f"{report_type.title()} Report", lines), mimetype="application/pdf", as_attachment=True, download_name=f"{report_type}_report.pdf")

    body = "\n".join(",".join(f'"{str(cell).replace(chr(34), chr(34)+chr(34))}"' for cell in row) for row in rows)
    return Response(body, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={report_type}_report.csv"})


@hr_bp.route("/ai-assistant", methods=["GET", "POST"])
@roles_required("admin", "employee")
def ai_assistant():

    answer = None
    tool = None
    question = ""

    if request.method == "POST":

        question = request.form.get("question", "").strip()

        employee = current_employee()
        employee_id = employee.id if employee else None

        tool = "Gemini AI"

        if question:
            answer = agent.process(employee_id, question)
        else:
            answer = "Please enter a question."

        db.session.add(
            AIChatLog(
                user_id=current_user.id,
                question=question,
                answer=answer,
                tool_used=tool
            )
        )

        log_activity("Asked Gemini Payroll Assistant", "AI")

        db.session.commit()

    logs_query = AIChatLog.query

    if current_user.is_employee():
        logs_query = logs_query.filter_by(user_id=current_user.id)

    return render_template(
        "modules/ai.html",
        answer=answer,
        question=question,
        tool=tool,
        logs=logs_query.order_by(AIChatLog.created_at.desc()).limit(30).all()
    )

def answer_hr_question(question):
    text = question.lower()
    employee = current_employee()
    if "salary" in text or "payroll" in text or "net" in text:
        query = Payroll.query
        if current_user.is_employee() and employee:
            query = query.filter_by(employee_id=employee.id)
        latest = query.order_by(Payroll.year.desc(), Payroll.month.desc()).first()
        if latest:
            return (f"Latest payroll for {latest.employee.full_name}: gross Rs. {money(latest.gross_salary)}, deductions Rs. {money(latest.total_deductions)}, net Rs. {money(latest.net_salary)}.", "payroll_lookup")
        return ("No payroll has been generated yet.", "payroll_lookup")
    if "leave" in text:
        if employee:
            balances = ", ".join(f"{b.leave_type}: {b.remaining} remaining" for b in employee.leave_balances)
            return (f"Your leave balances are {balances or 'not configured yet'}.", "leave_balance")
        return (f"There are {LeaveRequest.query.filter_by(status='Pending').count()} pending leave requests.", "leave_admin")
    if "attendance" in text:
        query = Attendance.query
        if current_user.is_employee() and employee:
            query = query.filter_by(employee_id=employee.id)
        return (f"Attendance records found: {query.count()}. Present: {query.filter_by(status='Present').count()}, Late: {query.filter_by(status='Late').count()}, Absent: {query.filter_by(status='Absent').count()}.", "attendance_summary")
    return ("I can answer salary, leave, attendance, payroll, and HR policy questions using the HRMS data available in this application.", "policy_faq")


@api_bp.route("/employees")
@login_required
def api_employees():
    return jsonify([employee_payload(item) for item in Employee.query.order_by(Employee.employee_code).all()])


@api_bp.route("/departments")
@login_required
def api_departments():
    return jsonify([
        {"id": item.id, "name": item.name, "code": item.code, "employee_count": len(item.employees), "head": item.head.full_name if item.head else None}
        for item in Department.query.order_by(Department.name).all()
    ])


@api_bp.route("/attendance")
@login_required
def api_attendance():
    return jsonify([
        {"employee": item.employee.full_name, "date": item.attendance_date.isoformat(), "status": item.status, "overtime_hours": money(item.overtime_hours)}
        for item in Attendance.query.order_by(Attendance.attendance_date.desc()).limit(200)
    ])


@api_bp.route("/leaves")
@login_required
def api_leaves():
    return jsonify([
        {"id": item.id, "employee": item.employee.full_name, "type": item.leave_type, "start_date": item.start_date.isoformat(), "end_date": item.end_date.isoformat(), "days": money(item.days), "status": item.status}
        for item in LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).limit(200)
    ])


@api_bp.route("/salary")
@login_required
def api_salary():
    return jsonify([
        {"employee": item.employee.full_name, "gross_salary": item.gross_salary, "fixed_deductions": item.fixed_deductions}
        for item in SalaryStructure.query.all()
    ])


@api_bp.route("/payroll")
@login_required
def api_payroll():
    return jsonify([payroll_payload(item) for item in Payroll.query.order_by(Payroll.year.desc(), Payroll.month.desc()).limit(200)])


@api_bp.route("/payslips")
@login_required
def api_payslips():
    return jsonify([
        {"id": item.id, "payroll_id": item.payroll_id, "employee": item.payroll.employee.full_name, "generated_at": item.generated_at.isoformat()}
        for item in Payslip.query.order_by(Payslip.generated_at.desc()).all()
    ])


@api_bp.route("/reports/summary")
@login_required
def api_report_summary():
    return jsonify({
        "employees": Employee.query.count(),
        "departments": Department.query.count(),
        "pending_leaves": LeaveRequest.query.filter_by(status="Pending").count(),
        "monthly_payroll": money(db.session.query(func.sum(Payroll.net_salary)).scalar()),
    })


@api_bp.route("/ai/logs")
@login_required
def api_ai_logs():
    return jsonify([
        {"user": item.user.username if item.user else "system", "question": item.question, "answer": item.answer, "tool_used": item.tool_used, "created_at": item.created_at.isoformat()}
        for item in AIChatLog.query.order_by(AIChatLog.created_at.desc()).limit(100)
    ])
