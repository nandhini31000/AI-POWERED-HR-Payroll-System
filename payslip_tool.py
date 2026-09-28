from app.services.payroll_service import PayrollService


class PayslipTool:

    @staticmethod
    def execute(employee_id):

        payroll = PayrollService.get_latest_payroll(employee_id)

        return {

            "month": payroll.month if payroll else "-",

            "year": payroll.year if payroll else "-",

            "gross": payroll.gross_salary if payroll else 0,

            "deduction": payroll.total_deductions if payroll else 0,

            "net": payroll.net_salary if payroll else 0
        }