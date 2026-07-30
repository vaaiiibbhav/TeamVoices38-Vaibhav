"""propose() / decide() / execute() for side-effecting actions.

`approvals` is append-only (same reject-update-delete trigger as traces/
ticket_events) — decide() can't UPDATE the PENDING row, so each call is a
new row carrying the same proposal_id, and "current status" of a proposal
is its latest row by created_at.

execute() takes only a proposal_id: it re-reads the approved payload from
the database and verifies its hash before running anything. No caller
(model or otherwise) has a path to pass a payload directly into execution.
"""
from __future__ import annotations

import hashlib
import json
import uuid

from services.api.db.pool import get_pool
from services.api.gateway.policy import risk_tier


def _payload_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _load_payload(row) -> dict:
    payload = row["payload"]
    return json.loads(payload) if isinstance(payload, str) else payload


async def _latest(pool, proposal_id: str):
    row = await pool.fetchrow(
        """
        SELECT * FROM approvals
        WHERE proposal_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        proposal_id,
    )
    if row is None:
        raise ValueError(f"no such proposal: {proposal_id}")
    return row


async def propose(*, action_type: str, ticket_id: str | None, payload: dict) -> str:
    proposal_id = str(uuid.uuid4())
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO approvals
            (id, proposal_id, ticket_id, status, action_type, payload,
             payload_hash, risk_tier)
        VALUES ($1, $2, $3, 'PENDING', $4, $5::jsonb, $6, $7)
        """,
        str(uuid.uuid4()), proposal_id, ticket_id, action_type,
        json.dumps(payload), _payload_hash(payload), risk_tier(action_type),
    )
    return proposal_id


async def decide(*, proposal_id: str, approved: bool, staff_id: str | None) -> str:
    pool = await get_pool()
    current = await _latest(pool, proposal_id)
    if current["status"] != "PENDING":
        raise ValueError(
            f"proposal {proposal_id} is {current['status']}, not PENDING"
        )

    status = "APPROVED" if approved else "REJECTED"
    await pool.execute(
        """
        INSERT INTO approvals
            (id, proposal_id, ticket_id, status, action_type, payload,
             payload_hash, risk_tier, decided_by)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9)
        """,
        str(uuid.uuid4()), proposal_id, current["ticket_id"], status,
        current["action_type"], current["payload"], current["payload_hash"],
        current["risk_tier"], staff_id,
    )
    return status


def _run_action(action_type: str, payload: dict) -> dict:
    """No real Composio/SMTP/Calendar integration yet — that's Phase 7.
    Simulated result, real enough to prove the propose/decide/execute
    lifecycle end-to-end without actually sending an email or booking a
    slot."""
    return {"simulated": True, "action_type": action_type, "payload": payload}


async def execute(proposal_id: str) -> dict:
    pool = await get_pool()
    current = await _latest(pool, proposal_id)
    if current["status"] != "APPROVED":
        raise ValueError(
            f"proposal {proposal_id} is {current['status']}, not APPROVED"
        )

    payload = _load_payload(current)
    if _payload_hash(payload) != current["payload_hash"]:
        raise ValueError(f"payload hash mismatch for proposal {proposal_id}")

    result = _run_action(current["action_type"], payload)

    await pool.execute(
        """
        INSERT INTO approvals
            (id, proposal_id, ticket_id, status, action_type, payload,
             payload_hash, risk_tier, result)
        VALUES ($1, $2, $3, 'EXECUTED', $4, $5::jsonb, $6, $7, $8::jsonb)
        """,
        str(uuid.uuid4()), proposal_id, current["ticket_id"],
        current["action_type"], current["payload"], current["payload_hash"],
        current["risk_tier"], json.dumps(result),
    )
    return result
