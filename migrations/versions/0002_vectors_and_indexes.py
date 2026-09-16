"""Persistent embeddings and support-query indexes."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_messages_conversation_id_id", "messages", ["conversation_id", "id"]),
    ("ix_feedback_conversation_id", "feedback", ["conversation_id"]),
    ("ix_feedback_message_id", "feedback", ["message_id"]),
    ("ix_tickets_conversation_id", "tickets", ["conversation_id"]),
    ("ix_tickets_message_id", "tickets", ["message_id"]),
    ("ix_tickets_status_created_at", "tickets", ["status", "created_at"]),
]


def upgrade():
    postgres = op.get_bind().dialect.name == "postgresql"
    if postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_vectors",
        sa.Column("snapshot_id", sa.String(64), primary_key=True),
        sa.Column("chunk_id", sa.String(200), primary_key=True),
        sa.Column("document_id", sa.String(200), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_model", sa.String(200), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector() if postgres else sa.JSON(), nullable=False),
    )
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)


def downgrade():
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
    op.drop_table("knowledge_vectors")
    # The extension may be shared with other applications; leave it installed.
