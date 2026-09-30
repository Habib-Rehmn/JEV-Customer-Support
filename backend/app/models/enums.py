from enum import StrEnum


class TicketStatus(StrEnum):
    NEW = "NEW"
    ANALYZING = "ANALYZING"
    JEV_FAILED = "JEV_FAILED"
    WAITING_FOR_AGENT = "WAITING_FOR_AGENT"
    WAITING_FOR_CUSTOMER = "WAITING_FOR_CUSTOMER"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class SupportAction(StrEnum):
    REFUND = "refund"
    REPLACEMENT = "replacement"
    TECHNICAL_SUPPORT = "technical_support"
    BILLING = "billing"
    HUMAN_ESCALATION = "human_escalation"


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    AGENT = "AGENT"
