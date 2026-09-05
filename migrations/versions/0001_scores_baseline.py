"""Baseline portável da tabela de pontuações.

Revision ID: 0001_scores_baseline
Revises:
Create Date: 2026-09-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_scores_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "scores" not in tables:
        op.create_table(
            "scores",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("data", sa.String(), nullable=False),
            sa.Column("total", sa.Integer(), nullable=False),
            sa.Column("acertos", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(), nullable=False, server_default=""),
            sa.Column("ip", sa.String(), nullable=False, server_default=""),
            sa.Column("ip_hash", sa.String(), nullable=False, server_default=""),
        )
    else:
        existing = {column["name"] for column in inspector.get_columns("scores")}
        missing = {
            "nome": sa.Column("nome", sa.String(), nullable=False, server_default=""),
            "ip": sa.Column("ip", sa.String(), nullable=False, server_default=""),
            "ip_hash": sa.Column("ip_hash", sa.String(), nullable=False, server_default=""),
        }
        for name, column in missing.items():
            if name not in existing:
                op.add_column("scores", column)

    # O IP bruto/mascarado é legado. Mantemos a coluna por compatibilidade de
    # schema, mas nenhum endereço fica persistido depois desta migração.
    op.execute(sa.text("UPDATE scores SET ip = '' WHERE ip <> ''"))

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("scores")}
    if "ix_scores_ip_hash_id" not in indexes:
        op.create_index("ix_scores_ip_hash_id", "scores", ["ip_hash", "id"], unique=False)


def downgrade() -> None:
    raise RuntimeError(
        "O baseline 0001 adota bancos SQLite já existentes e não pode ser "
        "revertido com segurança sem apagar dados. Restaure um backup em vez de downgrade."
    )
