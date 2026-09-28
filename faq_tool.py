class FAQTool:
    """
    Static, no-database HR/payroll glossary and policy reference.
    Used for generic definitional questions ("What is HRA?") so the
    model has grounded facts instead of guessing.
    """

    GLOSSARY = {
        "basic salary": "The fixed core component of pay before any allowances or deductions.",
        "hra": "House Rent Allowance - paid to help an employee cover housing/rent costs.",
        "da": "Dearness Allowance - a cost-of-living adjustment paid on top of basic salary.",
        "bonus": "An extra, performance- or occasion-linked payment added to salary.",
        "pf": "Provident Fund - a mandatory retirement savings contribution deducted from salary.",
        "professional tax": "A small state-government-levied tax deducted from salary each month.",
        "income tax": "Tax deducted from salary based on the employee's applicable tax slab.",
        "gross salary": "The total salary before deductions: Basic + HRA + DA + Bonus + Incentives.",
        "net salary": "Take-home pay after deductions: Gross Salary - PF - Professional Tax - Income Tax - Leave Deduction.",
        "leave deduction": "A reduction in salary applied for unpaid/excess leave days taken in a month.",
        "overtime": "Extra hours worked beyond standard hours, usually paid at a higher rate.",
    }

    LEAVE_POLICY = {
        "casual leave": "12 days per year",
        "earned leave": "15 days per year",
        "medical leave": "10 days per year",
    }

    @staticmethod
    def execute():
        return {
            "domain": "Payroll and HR",
            "glossary": FAQTool.GLOSSARY,
            "leave_policy": FAQTool.LEAVE_POLICY,
        }
