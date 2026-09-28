from app.models.employee_model import Employee
from app.models.hr_models import Payroll
from app.models.hr_models import Attendance
from app.models.hr_models import LeaveRequest
from app.models.hr_models import SalaryStructure


class PayrollService:

    @staticmethod
    def get_employee(employee_id):

        return Employee.query.get(employee_id)


    @staticmethod
    def get_latest_payroll(employee_id):

        return (
            Payroll.query
            .filter_by(employee_id=employee_id)
            .order_by(Payroll.year.desc(), Payroll.month.desc())
            .first()
        )


    @staticmethod
    def get_salary(employee_id):

        return SalaryStructure.query.filter_by(
            employee_id=employee_id
        ).first()


    @staticmethod
    def get_attendance(employee_id):

        return Attendance.query.filter_by(
            employee_id=employee_id
        ).all()


    @staticmethod
    def get_leave(employee_id):

        return LeaveRequest.query.filter_by(
            employee_id=employee_id
        ).all()