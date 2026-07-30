"""Intent -> department routing and ticket priority. Plain dicts and
threshold checks — never an LLM call.
"""
from __future__ import annotations

DEPARTMENT_ROUTING: dict[str, str] = {
    "exam_policy": "Examination Cell",
    "attendance_query": "Academic Office",
    "od_leave_request": "Academic Office",
    "hostel_issue": "Hostel Administration",
    "fee_scholarship": "Accounts & Finance",
    "certificate_request": "Academic Office",
    "placement_query": "Placement Cell",
    "library_query": "Library",
    "general_info": "Student Services",
    "out_of_scope": "Student Services",
}

URGENT = "URGENT"
HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"

SLA_HOURS: dict[str, int] = {
    URGENT: 1,
    HIGH: 8,
    MEDIUM: 48,
    LOW: 120,
}


def route_department(intent: str) -> str:
    return DEPARTMENT_ROUTING.get(intent, "Student Services")


def compute_priority(
    intent: str,
    hours_to_deadline: float | None = None,
    blocks_exam_or_scholarship: bool = False,
    residence_or_safety: bool = False,
) -> str:
    """hours_to_deadline is None when no deadline is known or applicable.
    blocks_exam_or_scholarship / residence_or_safety are caller-determined
    signals (e.g. from ticket-creation logic) — this function only applies
    the plain threshold rules from build_spec, it doesn't infer the signals
    itself."""
    if blocks_exam_or_scholarship:
        return URGENT
    if hours_to_deadline is not None and hours_to_deadline < 24:
        return URGENT
    if hours_to_deadline is not None and hours_to_deadline < 24 * 7:
        return HIGH
    if residence_or_safety:
        return HIGH
    if intent == "general_info":
        return LOW
    return MEDIUM
