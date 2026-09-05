"""Modelo acadêmico de participantes, tentativas e respostas.

Revision ID: 0002_attempt_analytics
Revises: 0001_scores_baseline
Create Date: 2026-09-05
"""

from __future__ import annotations

import unicodedata
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0002_attempt_analytics"
down_revision = "0001_scores_baseline"
branch_labels = None
depends_on = None


def _name_key(value: str) -> str:
    compact = " ".join((value or "").strip().split())
    normalized = unicodedata.normalize("NFKD", compact.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))[:120]


def _legacy_timestamp(value: str) -> datetime:
    raw = (value or "").strip()
    for parser in (datetime.fromisoformat, lambda text: datetime.strptime(text, "%Y-%m-%d %H:%M")):
        try:
            parsed = parser(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (TypeError, ValueError):
            pass
    return datetime.now(timezone.utc)


def upgrade() -> None:
    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_key", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_participants_name_key", "participants", ["name_key"], unique=False)

    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("participant_id", sa.Integer(), sa.ForeignKey("participants.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mode", sa.String(length=24), nullable=False),
        sa.Column("quiz_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("acertos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ip_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("legacy_score_id", sa.Integer(), nullable=True, unique=True),
    )
    op.create_index("ix_attempts_participant_id", "attempts", ["participant_id"], unique=False)
    op.create_index("ix_attempts_quiz_version", "attempts", ["quiz_version"], unique=False)
    op.create_index("ix_attempts_status", "attempts", ["status"], unique=False)
    op.create_index("ix_attempts_ip_hash", "attempts", ["ip_hash"], unique=False)

    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_key", sa.String(length=255), nullable=False),
        sa.Column("correct_code", sa.Integer(), nullable=False),
        sa.Column("answered_code", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("question_order", sa.Integer(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("attempt_id", "image_key", name="uq_answer_attempt_image"),
    )
    op.create_index("ix_answers_attempt_id", "answers", ["attempt_id"], unique=False)
    op.create_index("ix_answers_image_key", "answers", ["image_key"], unique=False)

    # Cada score legado vira uma tentativa concluída independente. Isso preserva
    # todos os resultados sem fingir que nomes iguais são necessariamente a
    # mesma pessoa; respostas individuais não existiam no schema antigo.
    bind = op.get_bind()
    scores = sa.table(
        "scores",
        sa.column("id", sa.Integer()),
        sa.column("data", sa.String()),
        sa.column("total", sa.Integer()),
        sa.column("acertos", sa.Integer()),
        sa.column("nome", sa.String()),
        sa.column("ip_hash", sa.String()),
    )
    participants = sa.table(
        "participants",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("name_key", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    attempts = sa.table(
        "attempts",
        sa.column("participant_id", sa.Integer()),
        sa.column("started_at", sa.DateTime(timezone=True)),
        sa.column("finished_at", sa.DateTime(timezone=True)),
        sa.column("mode", sa.String()),
        sa.column("quiz_version", sa.String()),
        sa.column("status", sa.String()),
        sa.column("total", sa.Integer()),
        sa.column("acertos", sa.Integer()),
        sa.column("ip_hash", sa.String()),
        sa.column("legacy_score_id", sa.Integer()),
    )

    for row in bind.execute(sa.select(scores).order_by(scores.c.id)).mappings():
        when = _legacy_timestamp(row["data"])
        name = (row["nome"] or "Anônimo").strip()[:100] or "Anônimo"
        participant_id = bind.execute(
            participants.insert()
            .values(name=name, name_key=_name_key(name), created_at=when)
            .returning(participants.c.id)
        ).scalar_one()
        bind.execute(
            attempts.insert().values(
                participant_id=participant_id,
                started_at=when,
                finished_at=when,
                mode="legacy",
                quiz_version="legacy-score-v1",
                status="completed",
                total=max(int(row["total"] or 0), 0),
                acertos=max(min(int(row["acertos"] or 0), int(row["total"] or 0)), 0),
                ip_hash=row["ip_hash"] or "",
                legacy_score_id=row["id"],
            )
        )


def downgrade() -> None:
    op.drop_index("ix_answers_image_key", table_name="answers")
    op.drop_index("ix_answers_attempt_id", table_name="answers")
    op.drop_table("answers")
    op.drop_index("ix_attempts_ip_hash", table_name="attempts")
    op.drop_index("ix_attempts_status", table_name="attempts")
    op.drop_index("ix_attempts_quiz_version", table_name="attempts")
    op.drop_index("ix_attempts_participant_id", table_name="attempts")
    op.drop_table("attempts")
    op.drop_index("ix_participants_name_key", table_name="participants")
    op.drop_table("participants")
