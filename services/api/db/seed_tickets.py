"""One-off seed: 8 fake tickets so the admin dashboard doesn't demo empty.
Run with: python -m services.api.db.seed_tickets
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from services.api.db.tickets import create_ticket

NOW = datetime.now(timezone.utc)

TICKETS = [
    dict(intent="exam_policy", department="Examination Cell", priority="URGENT",
         status="open", subject="[exam_policy] Hall ticket not generated for backlog paper",
         description="My hall ticket isn't showing the backlog subject I registered for.",
         sla_due_at=NOW - timedelta(hours=2)),  # overdue
    dict(intent="od_leave_request", department="Academic Office", priority="URGENT",
         status="open", subject="[od_leave_request] OD approval needed before tomorrow's fest",
         description="Need OD approval for the inter-college fest starting tomorrow.",
         sla_due_at=NOW + timedelta(minutes=45)),  # imminent
    dict(intent="attendance_query", department="Academic Office", priority="HIGH",
         status="open", subject="[attendance_query] Attendance shortfall dispute",
         description="My attendance % looks wrong for the odd semester.",
         sla_due_at=NOW + timedelta(hours=3)),  # due soon
    dict(intent="hostel_issue", department="Hostel Administration", priority="HIGH",
         status="in_progress", subject="[hostel_issue] Water leakage in room block C",
         description="Persistent water leakage near the electrical socket in room C-204.",
         sla_due_at=NOW + timedelta(hours=20)),
    dict(intent="fee_scholarship", department="Accounts & Finance", priority="MEDIUM",
         status="open", subject="[fee_scholarship] Scholarship disbursal not reflected",
         description="Scholarship amount hasn't reflected in the fee portal this semester.",
         sla_due_at=NOW + timedelta(days=2)),
    dict(intent="placement_query", department="Placement Cell", priority="MEDIUM",
         status="resolved", subject="[placement_query] Resume shortlist status query",
         description="Asked about shortlist status for the campus placement drive.",
         sla_due_at=NOW + timedelta(days=1)),
    dict(intent="library_query", department="Library", priority="LOW",
         status="open", subject="[library_query] Lost book fine waiver request",
         description="Requesting a fine waiver for a book lost during hostel relocation.",
         sla_due_at=NOW + timedelta(days=4)),
    dict(intent="general_info", department="Student Services", priority="LOW",
         status="closed", subject="[general_info] General campus navigation query",
         description="Asked for directions to the new academic block.",
         sla_due_at=NOW - timedelta(days=1)),  # closed, past due — shouldn't alarm
]


async def seed() -> None:
    for t in TICKETS:
        ticket_id = await create_ticket(**t)
        print(f"created {ticket_id}  {t['department']:<24} {t['priority']:<7} {t['status']}")


if __name__ == "__main__":
    asyncio.run(seed())
