"""Risk tiers for side-effecting actions. Plain dict, never an LLM call —
low tier auto-executes, medium/high require a staff approval row.
"""
from __future__ import annotations

RISK_TIERS: dict[str, str] = {
    "answer": "LOW",
    "create_ticket": "LOW",
    "draft_email": "LOW",
    "calendar_event": "MEDIUM",
    "close_ticket": "MEDIUM",
    "reprioritize_ticket": "MEDIUM",
    "send_email": "HIGH",
    "grade_change": "HIGH",
    "fee_change": "HIGH",
}


def risk_tier(action_type: str) -> str:
    return RISK_TIERS.get(action_type, "HIGH")


def requires_approval(action_type: str) -> bool:
    return risk_tier(action_type) != "LOW"
