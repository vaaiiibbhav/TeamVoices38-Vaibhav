"""initial schema

Revision ID: dbaea2ba8ac2
Revises:
Create Date: 2026-07-29 09:16:45.105565

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'dbaea2ba8ac2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE documents (
            id              UUID PRIMARY KEY,
            title           TEXT NOT NULL,
            doc_type        TEXT NOT NULL,
            source_path     TEXT NOT NULL,
            effective_date  DATE,
            superseded_by   UUID REFERENCES documents(id),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE doc_chunks (
            id           UUID PRIMARY KEY,
            document_id  UUID NOT NULL REFERENCES documents(id),
            page         INT NOT NULL,
            section      TEXT NOT NULL,
            chunk_text   TEXT NOT NULL,
            header       TEXT NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE students (
            id           UUID PRIMARY KEY,
            roll_number  TEXT NOT NULL UNIQUE,
            name         TEXT NOT NULL,
            email        TEXT NOT NULL,
            program      TEXT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE staff (
            id          UUID PRIMARY KEY,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL,
            department  TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'staff',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE conversations (
            id               UUID PRIMARY KEY,
            student_id       UUID REFERENCES students(id),
            started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_message_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE traces (
            id                    UUID PRIMARY KEY,
            conversation_id       UUID REFERENCES conversations(id),
            question              TEXT NOT NULL,
            intent                TEXT,
            slots                 JSONB NOT NULL DEFAULT '{}',
            confidence            DOUBLE PRECISION NOT NULL,
            confidence_breakdown  JSONB NOT NULL,
            reason_codes          JSONB NOT NULL DEFAULT '[]',
            route                 TEXT NOT NULL,
            path                  JSONB NOT NULL,
            answer                TEXT,
            sources               JSONB NOT NULL DEFAULT '[]',
            latency_ms            DOUBLE PRECISION NOT NULL,
            pending_approval      BOOLEAN NOT NULL DEFAULT false,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE messages (
            id               UUID PRIMARY KEY,
            conversation_id  UUID NOT NULL REFERENCES conversations(id),
            role             TEXT NOT NULL,
            content          TEXT NOT NULL,
            trace_id         UUID REFERENCES traces(id),
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE tickets (
            id               UUID PRIMARY KEY,
            conversation_id  UUID REFERENCES conversations(id),
            trace_id         UUID REFERENCES traces(id),
            student_id       UUID REFERENCES students(id),
            intent           TEXT NOT NULL,
            department       TEXT NOT NULL,
            priority         TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'open',
            subject          TEXT NOT NULL,
            description      TEXT NOT NULL,
            sla_due_at       TIMESTAMPTZ NOT NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE ticket_events (
            id          UUID PRIMARY KEY,
            ticket_id   UUID NOT NULL REFERENCES tickets(id),
            event_type  TEXT NOT NULL,
            actor       UUID REFERENCES staff(id),
            payload     JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE approvals (
            id            UUID PRIMARY KEY,
            proposal_id   UUID NOT NULL,
            ticket_id     UUID REFERENCES tickets(id),
            status        TEXT NOT NULL,
            action_type   TEXT NOT NULL,
            payload       JSONB,
            payload_hash  TEXT,
            risk_tier     TEXT,
            decided_by    UUID REFERENCES staff(id),
            result        JSONB,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE corrections (
            id                UUID PRIMARY KEY,
            trace_id          UUID NOT NULL REFERENCES traces(id),
            staff_id          UUID NOT NULL REFERENCES staff(id),
            corrected_answer  TEXT NOT NULL,
            note              TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Append-only enforcement: traces, ticket_events, approvals reject any
    # UPDATE or DELETE, regardless of which role runs the query (unlike
    # REVOKE, this also binds the table owner).
    op.execute("""
        CREATE OR REPLACE FUNCTION reject_update_delete() RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only: % not allowed', TG_TABLE_NAME, TG_OP;
        END;
        $$ LANGUAGE plpgsql
    """)

    for table in ("traces", "ticket_events", "approvals"):
        op.execute(f"""
            CREATE TRIGGER {table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_update_delete()
        """)


def downgrade() -> None:
    for table in ("traces", "ticket_events", "approvals"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
    op.execute("DROP FUNCTION IF EXISTS reject_update_delete()")

    for table in (
        "corrections",
        "approvals",
        "ticket_events",
        "tickets",
        "messages",
        "traces",
        "conversations",
        "staff",
        "students",
        "doc_chunks",
        "documents",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
