from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import csrf
from app import db
from app.models.hr_models import AIChatLog
from app.agent.payroll_agent import agent
from app.utils.decorators import roles_required

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/chatbot")
@roles_required("admin", "employee")
def chatbot_page():
    """
    Renders the ChatGPT-style AI Payroll Assistant UI (chatbot.html).
    The page itself just loads static markup/JS; every message it sends
    goes to POST /chat below.
    """
    return render_template("chatbot.html")


@chatbot_bp.route("/chat", methods=["POST"])
@csrf.exempt
@login_required
def chat():

    data = request.get_json(silent=True) or {}

    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({
            "reply": "Please enter a message."
        })

    employee = getattr(current_user, "employee", None)
    employee_id = employee.id if employee else None

    reply = agent.process(employee_id, question)

    log = AIChatLog(
        user_id=current_user.id,
        question=question,
        answer=reply,
        tool_used="Gemini"
    )

    db.session.add(log)
    db.session.commit()

    return jsonify({
        "reply": reply
    })
