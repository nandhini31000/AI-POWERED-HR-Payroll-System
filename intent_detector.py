"""
intent_detector.py
-------------------
Fast, free, local intent detection for the payroll chatbot.

This is a plain keyword matcher deliberately used INSTEAD of an extra
Gemini call. Two upsides for a student project: (1) zero extra API
latency/cost per message, and (2) the chatbot still routes correctly even
if the AI provider is briefly unavailable, since only the final answer
(not the routing) depends on Gemini.
"""


class IntentDetector:

    @staticmethod
    def detect(question):

        text = (question or "").lower()

        # Greeting - checked first so "hi, what's my salary" still greets
        if any(word in text for word in ["hi", "hello", "hey", "good morning", "good evening"]) and len(text.split()) <= 4:
            return "greeting"

        # Help / capabilities
        if any(phrase in text for phrase in ["what can you do", "help me", "how can you help", "menu"]):
            return "help"

        # Definitional / FAQ questions ("what is HRA", "define PF")
        if text.startswith("what is") or text.startswith("define") or "meaning of" in text:
            return "faq"

        # Comparison
        if any(word in text for word in ["compare", "difference", "vs", "last month", "previous month"]):
            return "comparison"

        # Payslip
        if any(word in text for word in ["payslip", "pay slip", "salary slip"]):
            return "payslip"

        # Leave
        if any(word in text for word in ["leave", "vacation", "holiday", "casual leave", "medical leave", "earned leave"]):
            return "leave"

        # Attendance
        if any(word in text for word in ["attendance", "present", "absent", "late arrival", "overtime", "check-in", "check in", "check-out"]):
            return "attendance"

        # Deductions (PF, tax, HRA, DA, bonus)
        if any(word in text for word in ["pf", "provident fund", "hra", "da", "dearness", "tax", "deduction", "bonus"]):
            return "deduction"

        # Salary / general pay questions
        if any(word in text for word in ["salary", "gross", "net pay", "net salary", "income", "earn", "basic salary", "ctc"]):
            return "salary"

        # Company / HR policy questions
        if any(word in text for word in ["policy", "policies", "rule", "eligib"]):
            return "faq"

        return "general"
