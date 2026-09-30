"""Policy text given to OpenAI for each permitted action.

OpenAI may only state what is written here, so edit these to match your real support policies.
"""
from app.models.enums import SupportAction

POLICIES: dict[SupportAction, list[str]] = {
    SupportAction.REPLACEMENT: [
        "A replacement is approved for this order.",
        "The replacement ships within 1-2 business days.",
        "Tracking details are emailed once it ships.",
    ],
    SupportAction.REFUND: [
        "A refund of the order total is approved.",
        "The refund goes back to the original payment method.",
        "Refunds usually appear within 5-10 business days, depending on the bank.",
    ],
    SupportAction.TECHNICAL_SUPPORT: [
        "Acknowledge the problem and offer help.",
        "Ask for the details needed to troubleshoot: device or browser, the steps taken, and any error message.",
        "Do not claim the problem is already fixed.",
    ],
    SupportAction.BILLING: [
        "The billing team will review the account and reply within 1-2 business days.",
        "Do not promise refunds, credits or charge reversals.",
    ],
    SupportAction.HUMAN_ESCALATION: [
        "A support specialist will review this request personally.",
        "The customer will hear back within 1 business day.",
        "Do not promise any specific outcome, refund or replacement.",
    ],
}
