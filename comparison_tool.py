from app.models.hr_models import Payroll


class ComparisonTool:

    @staticmethod
    def execute(employee_id):

        payrolls = (

            Payroll.query

            .filter_by(employee_id=employee_id)

            .order_by(Payroll.year.desc(), Payroll.month.desc())

            .limit(2)

            .all()

        )

        return payrolls