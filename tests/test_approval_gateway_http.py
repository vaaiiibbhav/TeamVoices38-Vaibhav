"""HTTP-level guard tests for the approval gateway's decide/execute routes —
proves the guards (execute-on-pending, decide-on-executed) hold through the
real FastAPI routes in main.py, not just the direct gateway.approval calls
already verified live in Phase 5.

Setup (propose) and the HTTP calls share one asyncio loop deliberately: the
asyncpg pool is loop-bound, and TestClient's thread-portal would attach it to
a second loop. httpx.AsyncClient + ASGITransport keeps everything on one loop.

Run with: python tests/test_approval_gateway_http.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from services.api.gateway.approval import propose
from services.api.main import app


async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        proposal_id = await propose(
            action_type="calendar_event", ticket_id=None,
            payload={"title": "test event"},
        )

        # execute-on-pending: never approved, must be rejected
        r = await client.post(f"/api/approvals/{proposal_id}/execute")
        assert r.status_code == 409, r.text
        assert "not APPROVED" in r.json()["detail"]

        # approve it for real, then execute for real
        r = await client.post(
            f"/api/approvals/{proposal_id}/decide",
            json={"approved": True, "staff_id": "test-staff"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "APPROVED"

        r = await client.post(f"/api/approvals/{proposal_id}/execute")
        assert r.status_code == 200, r.text
        assert r.json()["result"]["simulated"] is True

        # decide-on-executed: already EXECUTED, must be rejected
        r = await client.post(
            f"/api/approvals/{proposal_id}/decide",
            json={"approved": True, "staff_id": "test-staff"},
        )
        assert r.status_code == 409, r.text
        assert "not PENDING" in r.json()["detail"]

    print("test_approval_gateway_http: all assertions passed")


asyncio.run(main())
