from app.services.payroll_service import PayrollService


class AttendanceTool:

    @staticmethod
    def execute(employee_id):

        attendance = PayrollService.get_attendance(employee_id)

        result = []

        for row in attendance:

            result.append({

                "date": str(row.attendance_date),

                "status": row.status,

                "overtime": float(row.overtime_hours)

            })

        return result