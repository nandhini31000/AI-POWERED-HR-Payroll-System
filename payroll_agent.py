from gemini_helper import ask_gemini

from app.agent.router import Router
from app.agent.salary_tool import SalaryTool
from app.agent.attendance_tool import AttendanceTool
from app.agent.leave_tool import LeaveTool
from app.agent.payslip_tool import PayslipTool
from app.agent.comparison_tool import ComparisonTool
from app.agent.faq_tool import FAQTool
from app.agent.memory import memory
from app.services.payroll_service import PayrollService
from app.services.prompt_builder import build_prompt

HELP_REPLY = """### 👋 I'm PayrollGPT, your AI HR Assistant

I can help you with:

- 💰 **Salary Breakdown** - "Explain my salary"
- 📄 **Payslip Explanation** - "Explain my payslip"
- 🏦 **PF & Tax** - "Why was PF deducted?"
- 📅 **Attendance** - "Show my attendance"
- 🌴 **Leave Details** - "What's my leave balance?"
- 📊 **Salary Comparison** - "Compare this month with last month"
- ❓ **Payroll FAQs** - "What is HRA?"

Just ask me a question in plain English!"""


class PayrollAgent:
    """
    Single entry point for the chatbot.

    Flow per message:
      1. Route the question to a tool (fast, local, no API call).
      2. Fetch only the data that tool needs from the database.
      3. Build ONE prompt (system persona + history + data + question).
      4. Make exactly ONE Gemini call for the final answer.
      5. Save the turn to short-term conversation memory.

    Greetings / "what can you do" are answered instantly without calling
    the AI at all, so they always work even if Gemini is unavailable.
    """

    def process(self, employee_id, question):

        question = (question or "").strip()

        if not question:
            return "Please type a question so I can help you."

        employee = PayrollService.get_employee(employee_id)
        employee_name = employee.full_name if employee else "Employee"

        tool = Router.get_tool(question)

        if tool == "greeting":
            return f"👋 Hello **{employee_name}**! I'm PayrollGPT, your AI HR Assistant. How can I help you today?"

        if tool == "help":
            return HELP_REPLY

        # FAQ questions (e.g. "What is HRA?") are generic HR/payroll
        # definitions and don't need an employee profile to answer.
        needs_employee_profile = tool not in ("faq", "general")

        if needs_employee_profile and employee_id is None:
            return (
                "I couldn't find an employee profile linked to this account, "
                "so I can't look up personal payroll data. If you're testing "
                "as an admin, log in as an employee account instead, or ask "
                "me a general question like \"What is HRA?\"."
            )

        try:
            if tool in ("salary", "deduction"):
                data = SalaryTool.execute(employee_id)

            elif tool == "attendance":
                data = AttendanceTool.execute(employee_id)

            elif tool == "leave":
                data = LeaveTool.execute(employee_id)

            elif tool == "payslip":
                data = PayslipTool.execute(employee_id)

            elif tool == "comparison":
                data = ComparisonTool.execute(employee_id)

            elif tool == "faq":
                data = FAQTool.execute()

            else:
                data = {}

        except Exception as exc:  # pragma: no cover - db issues, etc.
            return f"⚠️ I couldn't fetch your payroll data right now ({exc}). Please try again shortly."

        history = memory.get_history(employee_id)

        prompt = build_prompt(
            employee_name=employee_name,
            tool=tool,
            data=data,
            history=history,
            question=question,
        )

        answer = ask_gemini(prompt)

        memory.add_message(employee_id, "User", question)
        memory.add_message(employee_id, "Assistant", answer)

        return answer


agent = PayrollAgent()
