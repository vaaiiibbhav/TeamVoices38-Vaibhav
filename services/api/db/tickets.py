"""Raw SQL against the `tickets` table — no ORM, matches migrations/."""
from __future__ import annotations

import uuid
from datetime import datetime

from services.api.db.pool import get_pool


async def create_ticket(
    *,
    intent: str,
    department: str,
    priority: str,
    subject: str,
    description: str,
    sla_due_at: datetime,
    conversation_id: str | None = None,
    trace_id: str | None = None,
    student_id: str | None = None,
    status: str = "open",
) -> str:
    ticket_id = str(uuid.uuid4())
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO tickets
            (id, conversation_id, trace_id, student_id, intent, department,
             priority, status, subject, description, sla_due_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
        ticket_id, conversation_id, trace_id, student_id, intent, department,
        priority, status, subject, description, sla_due_at,
    )
    return ticket_id


async def list_tickets(
    *,
    department: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> list[dict]:
    pool = await get_pool()
    conditions = []
    args = []
    for column, value in (
        ("department", department),
        ("priority", priority),
        ("status", status),
    ):
        if value is not None:
            args.append(value)
            conditions.append(f"{column} = ${len(args)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = await pool.fetch(
        f"""
        SELECT id, intent, department, priority, status, subject,
               description, sla_due_at, created_at
        FROM tickets
        {where}
        ORDER BY sla_due_at ASC
        """,
        *args,
    )
    return [dict(row) for row in rows]
