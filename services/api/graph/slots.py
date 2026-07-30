"""Required slots per intent. Campus intents only."""
from __future__ import annotations

CAMPUS_INTENTS = [
    "exam_policy",
    "attendance_query",
    "od_leave_request",
    "hostel_issue",
    "fee_scholarship",
    "certificate_request",
    "placement_query",
    "library_query",
    "general_info",
    "out_of_scope",
]

REQUIRED_SLOTS: dict[str, list[str]] = {
    "exam_policy": [],
    "attendance_query": [],
    "od_leave_request": ["event_date", "event_reason"],
    "hostel_issue": ["issue_type"],
    "fee_scholarship": [],
    "certificate_request": ["certificate_type"],
    "placement_query": [],
    "library_query": [],
    "general_info": [],
    "out_of_scope": [],
}


def missing_slots(intent: str, slots: dict[str, str]) -> list[str]:
    required = REQUIRED_SLOTS.get(intent, [])
    return [name for name in required if not slots.get(name)]
