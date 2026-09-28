from app.services.payroll_service import PayrollService


class SalaryTool:

    @staticmethod
    def execute(employee_id):

        salary = PayrollService.get_salary(employee_id)
        payroll = PayrollService.get_latest_payroll(employee_id)

        return {

            "basic_salary": salary.basic_salary if salary else 0,

            "hra": salary.hra if salary else 0,

            "da": salary.da if salary else 0,

            "bonus": salary.bonus if salary else 0,

            "pf": salary.pf if salary else 0,

            "professional_tax": salary.professional_tax if salary else 0,

            "income_tax": salary.income_tax if salary else 0,

            "gross_salary": payroll.gross_salary if payroll else 0,

            "net_salary": payroll.net_salary if payroll else 0
        }