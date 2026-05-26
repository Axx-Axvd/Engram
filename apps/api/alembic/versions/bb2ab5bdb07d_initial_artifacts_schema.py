"""initial artifacts schema

Revision ID: bb2ab5bdb07d
Revises:
Create Date: 2026-05-26 20:39:37.732984

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bb2ab5bdb07d"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Native PG enum types. Created explicitly (create_type=False on columns) so a type shared by
# several tables is created exactly once.
artifact_type = postgresql.ENUM(
    "requirement", "user_story", "task", "test_case", "change_request", name="artifact_type"
)
artifact_status = postgresql.ENUM(
    "draft", "reviewed", "approved", "changed", "active", "archived",
    "proposed", "in_review", "rejected", "applied", name="artifact_status",
)
link_type = postgresql.ENUM(
    "refines", "implements", "tests", "changes", "depends_on", "derived_from", "related_to",
    name="link_type",
)
change_action = postgresql.ENUM(
    "created", "updated", "status_changed", "version_created", "linked", "unlinked",
    name="change_action",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    bind = op.get_bind()
    for enum in (artifact_type, artifact_status, link_type, change_action):
        enum.create(bind, checkfirst=True)

    artifact_type_col = postgresql.ENUM(name="artifact_type", create_type=False)
    artifact_status_col = postgresql.ENUM(name="artifact_status", create_type=False)
    link_type_col = postgresql.ENUM(name="link_type", create_type=False)
    change_action_col = postgresql.ENUM(name="change_action", create_type=False)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", artifact_type_col, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", artifact_status_col, nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("source_ref", sa.String(length=500), nullable=True),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=384), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("updated_by", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_artifacts_status"), "artifacts", ["status"], unique=False)
    op.create_index(op.f("ix_artifacts_type"), "artifacts", ["type"], unique=False)

    op.create_table(
        "artifact_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("type", link_type_col, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "target_id", "type", name="uq_artifact_link"),
    )
    op.create_index(op.f("ix_artifact_links_source_id"), "artifact_links", ["source_id"], unique=False)
    op.create_index(op.f("ix_artifact_links_target_id"), "artifact_links", ["target_id"], unique=False)
    op.create_index(op.f("ix_artifact_links_type"), "artifact_links", ["type"], unique=False)

    op.create_table(
        "artifact_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", artifact_status_col, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artifact_id", "version", name="uq_artifact_version"),
    )
    op.create_index(
        op.f("ix_artifact_versions_artifact_id"), "artifact_versions", ["artifact_id"], unique=False
    )

    op.create_table(
        "change_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=True),
        sa.Column("action", change_action_col, nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_change_logs_artifact_id"), "change_logs", ["artifact_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_change_logs_artifact_id"), table_name="change_logs")
    op.drop_table("change_logs")
    op.drop_index(op.f("ix_artifact_versions_artifact_id"), table_name="artifact_versions")
    op.drop_table("artifact_versions")
    op.drop_index(op.f("ix_artifact_links_type"), table_name="artifact_links")
    op.drop_index(op.f("ix_artifact_links_target_id"), table_name="artifact_links")
    op.drop_index(op.f("ix_artifact_links_source_id"), table_name="artifact_links")
    op.drop_table("artifact_links")
    op.drop_index(op.f("ix_artifacts_type"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_status"), table_name="artifacts")
    op.drop_table("artifacts")

    bind = op.get_bind()
    for enum in (artifact_type, artifact_status, link_type, change_action):
        enum.drop(bind, checkfirst=True)
