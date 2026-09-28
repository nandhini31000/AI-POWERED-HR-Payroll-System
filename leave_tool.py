from app.services.payroll_service import PayrollService


class LeaveTool:

    @staticmethod
    def execute(employee_id):

        leaves = PayrollService.get_leave(employee_id)

        result = []

        for row in leaves:

            result.append({

                "type": row.leave_type,

                "status": row.status,

                "start": str(row.start_date),

                "end": str(row.end_date)

            })

        return result