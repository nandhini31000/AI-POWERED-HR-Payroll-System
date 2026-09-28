from app.services.intent_detector import IntentDetector


class Router:
    """Maps a detected intent to the data-fetching tool that should run."""

    INTENT_TO_TOOL = {
        "salary": "salary",
        "deduction": "deduction",
        "attendance": "attendance",
        "leave": "leave",
        "payslip": "payslip",
        "comparison": "comparison",
        "faq": "faq",
        "greeting": "greeting",
        "help": "help",
    }

    @staticmethod
    def get_tool(question):
        intent = IntentDetector.detect(question)
        return Router.INTENT_TO_TOOL.get(intent, "general")
