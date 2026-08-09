"""true path domain model

Revision ID: c41f0e9a2b11
Revises: bff93959505e
Create Date: 2026-08-01
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "c41f0e9a2b11"
down_revision: str | Sequence[str] | None = "bff93959505e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
MANUAL_SOURCE_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")
MANUAL_REVISION_ID = uuid.UUID("00000000-0000-0000-0000-000000000201")


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False, server_default="system"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"], unique=True)
    op.create_index("ix_projects_is_default", "projects", ["is_default"])

    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("configuration", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False, server_default="system"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_source_project_name"),
    )
    op.create_index("ix_sources_project_id", "sources", ["project_id"])
    op.create_index("ix_sources_kind", "sources", ["kind"])

    op.create_table(
        "source_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.String(200), nullable=False),
        sa.Column("revision_url", sa.String(1000), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "revision", name="uq_source_revision"),
    )
    op.create_index("ix_source_revisions_project_id", "source_revisions", ["project_id"])
    op.create_index("ix_source_revisions_source_id", "source_revisions", ["source_id"])
    op.create_index("ix_source_revisions_revision", "source_revisions", ["revision"])

    op.create_table(
        "source_locators",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_revision_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False, server_default="file"),
        sa.Column("path", sa.String(1000), nullable=True),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(1500), nullable=True),
        sa.Column("external_id", sa.String(300), nullable=True),
        sa.Column("content_hash", sa.String(128), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_revision_id"], ["source_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_locators_project_id", "source_locators", ["project_id"])
    op.create_index("ix_source_locators_source_revision_id", "source_locators", ["source_revision_id"])
    op.create_index("ix_source_locators_path", "source_locators", ["path"])

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO projects (id, name, slug, description, is_default, created_by) "
            "VALUES (:id, 'Default project', 'default', "
            "'Migrated prototype data and legacy API operations.', true, 'migration')"
        ),
        {"id": DEFAULT_PROJECT_ID},
    )
    bind.execute(
        sa.text(
            "INSERT INTO sources (id, project_id, kind, name, configuration, created_by) "
            "VALUES (:id, :project_id, 'manual', 'Manual and legacy input', "
            "'{}'::jsonb, 'migration')"
        ),
        {"id": MANUAL_SOURCE_ID, "project_id": DEFAULT_PROJECT_ID},
    )
    bind.execute(
        sa.text(
            "INSERT INTO source_revisions "
            "(id, project_id, source_id, revision, metadata_json) "
            "VALUES (:id, :project_id, :source_id, 'legacy-baseline', "
            "'{\"migration\": true}'::jsonb)"
        ),
        {
            "id": MANUAL_REVISION_ID,
            "project_id": DEFAULT_PROJECT_ID,
            "source_id": MANUAL_SOURCE_ID,
        },
    )

    op.add_column("artifacts", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.add_column("artifacts", sa.Column("source_locator_id", sa.Uuid(), nullable=True))
    bind.execute(
        sa.text("UPDATE artifacts SET project_id = :project_id"),
        {"project_id": DEFAULT_PROJECT_ID},
    )
    op.alter_column("artifacts", "project_id", nullable=False)
    op.create_foreign_key(
        "fk_artifacts_project", "artifacts", "projects", ["project_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_artifacts_source_locator",
        "artifacts",
        "source_locators",
        ["source_locator_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_artifacts_project_id", "artifacts", ["project_id"])
    op.create_index("ix_artifacts_source_locator_id", "artifacts", ["source_locator_id"])

    op.add_column("artifact_links", sa.Column("project_id", sa.Uuid(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE artifact_links l SET project_id = a.project_id "
            "FROM artifacts a WHERE a.id = l.source_id"
        )
    )
    op.alter_column("artifact_links", "project_id", nullable=False)
    op.create_foreign_key(
        "fk_artifact_links_project",
        "artifact_links",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_artifact_links_project_id", "artifact_links", ["project_id"])

    op.add_column("change_logs", sa.Column("project_id", sa.Uuid(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE change_logs c SET project_id = COALESCE(a.project_id, :default_id) "
            "FROM artifacts a WHERE a.id = c.artifact_id"
        ),
        {"default_id": DEFAULT_PROJECT_ID},
    )
    bind.execute(
        sa.text("UPDATE change_logs SET project_id = :default_id WHERE project_id IS NULL"),
        {"default_id": DEFAULT_PROJECT_ID},
    )
    op.alter_column("change_logs", "project_id", nullable=False)
    op.create_foreign_key(
        "fk_change_logs_project",
        "change_logs",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_change_logs_project_id", "change_logs", ["project_id"])

    op.create_table(
        "artifact_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=True),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("source_locator_id", sa.Uuid(), nullable=True),
        sa.Column("embedding", Vector(dim=384), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_locator_id"], ["source_locators.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "artifact_id", "key", name="uq_item_artifact_key"),
    )
    for column in ("project_id", "artifact_id", "type", "status", "source_locator_id"):
        op.create_index(f"ix_artifact_items_{column}", "artifact_items", [column])

    op.create_table(
        "item_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("source_revision_id", sa.Uuid(), nullable=True),
        sa.Column("source_locator_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False, server_default="system"),
        sa.ForeignKeyConstraint(["item_id"], ["artifact_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_revision_id"], ["source_revisions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_locator_id"], ["source_locators.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", "version", name="uq_item_version"),
    )
    for column in ("item_id", "source_revision_id", "is_active"):
        op.create_index(f"ix_item_versions_{column}", "item_versions", [column])
    op.create_foreign_key(
        "fk_item_current_version",
        "artifact_items",
        "item_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    link_type = postgresql.ENUM(name="link_type", create_type=False)
    op.create_table(
        "item_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_item_id", sa.Uuid(), nullable=False),
        sa.Column("target_item_id", sa.Uuid(), nullable=False),
        sa.Column("type", link_type, nullable=False),
        sa.Column("origin", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "evidence_locator_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("state", sa.String(30), nullable=False, server_default="confirmed"),
        sa.Column("source_revision_id", sa.Uuid(), nullable=True),
        sa.Column("confirmed_by", sa.String(200), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_item_id"], ["artifact_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_item_id"], ["artifact_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_revision_id"], ["source_revisions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_item_id", "target_item_id", "type", name="uq_item_link"),
    )
    for column in ("project_id", "source_item_id", "target_item_id", "type", "origin", "state"):
        op.create_index(f"ix_item_links_{column}", "item_links", [column])

    op.create_table(
        "evidence_refs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_locator_id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(50), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("digest", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_locator_id"], ["source_locators.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("project_id", "source_locator_id", "subject_type", "subject_id"):
        op.create_index(f"ix_evidence_refs_{column}", "evidence_refs", [column])

    _create_analysis_tables()
    _backfill_legacy_items(bind)


def _create_analysis_tables() -> None:
    op.create_table(
        "impact_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_revision_id", sa.Uuid(), nullable=True),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="in_review"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_provider", sa.String(100), nullable=False, server_default="mock"),
        sa.Column("model_name", sa.String(200), nullable=True),
        sa.Column("algorithm_version", sa.String(50), nullable=False, server_default="impact-v1"),
        sa.Column("retrieval_mode", sa.String(30), nullable=False, server_default="combined"),
        sa.Column("context_budget", sa.Integer(), nullable=False, server_default="4000"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False, server_default="system"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_revision_id"], ["source_revisions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("project_id", "source_revision_id", "status", "retrieval_mode"):
        op.create_index(f"ix_impact_analyses_{column}", "impact_analyses", [column])

    op.create_table(
        "impact_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("item_version_id", sa.Uuid(), nullable=False),
        sa.Column("impact_type", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("proposed_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("selection_reason", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("decision", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["impact_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["artifact_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_version_id"], ["item_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "item_id", name="uq_analysis_candidate_item"),
    )
    for column in ("analysis_id", "item_id", "item_version_id", "impact_type", "decision"):
        op.create_index(f"ix_impact_candidates_{column}", "impact_candidates", [column])

    op.create_table(
        "context_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False, server_default="system"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["impact_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_context_packages_project_id", "context_packages", ["project_id"])
    op.create_index("ix_context_packages_analysis_id", "context_packages", ["analysis_id"])

    op.create_table(
        "context_package_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("item_version_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("reason", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("graph_path", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.ForeignKeyConstraint(["package_id"], ["context_packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["artifact_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_version_id"], ["item_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_id", "item_version_id", name="uq_package_item_version"),
    )
    for column in ("package_id", "item_id", "item_version_id"):
        op.create_index(f"ix_context_package_items_{column}", "context_package_items", [column])

    op.create_table(
        "change_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=True),
        sa.Column("source_revision_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(300), nullable=False),
        sa.Column("external_url", sa.String(1500), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="imported"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["impact_analyses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_revision_id"], ["source_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("project_id", "analysis_id", "source_revision_id", "external_id"):
        op.create_index(f"ix_change_sets_{column}", "change_sets", [column])

    op.create_table(
        "change_set_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("change_set_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("before_version_id", sa.Uuid(), nullable=True),
        sa.Column("after_version_id", sa.Uuid(), nullable=True),
        sa.Column("change_kind", sa.String(30), nullable=False, server_default="modified"),
        sa.ForeignKeyConstraint(["change_set_id"], ["change_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["artifact_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["before_version_id"], ["item_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["after_version_id"], ["item_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_change_set_items_change_set_id", "change_set_items", ["change_set_id"])
    op.create_index("ix_change_set_items_item_id", "change_set_items", ["item_id"])


def _backfill_legacy_items(bind) -> None:
    artifacts = bind.execute(
        sa.text(
            "SELECT id, type::text AS type, title, content, items, status::text AS status, "
            "source_ref, created_by FROM artifacts"
        )
    ).mappings()
    item_ids: dict[tuple[uuid.UUID, str], uuid.UUID] = {}
    pending_refs: list[tuple[uuid.UUID, str, str, str]] = []
    type_map = {
        "project_brief": "document",
        "requirement": "requirement",
        "user_story": "user_story",
        "task": "task",
        "test_case": "test",
        "change_request": "change_request",
    }
    for artifact in artifacts:
        locator_id = uuid.uuid4()
        content = artifact["content"] or ""
        bind.execute(
            sa.text(
                "INSERT INTO source_locators "
                "(id, project_id, source_revision_id, kind, path, external_id, content_hash) "
                "VALUES (:id, :project_id, :revision_id, 'legacy_artifact', :path, :external_id, :hash)"
            ),
            {
                "id": locator_id,
                "project_id": DEFAULT_PROJECT_ID,
                "revision_id": MANUAL_REVISION_ID,
                "path": f"artifact/{artifact['id']}",
                "external_id": artifact["source_ref"],
                "hash": hashlib.sha256(content.encode()).hexdigest(),
            },
        )
        bind.execute(
            sa.text("UPDATE artifacts SET source_locator_id = :locator WHERE id = :id"),
            {"locator": locator_id, "id": artifact["id"]},
        )
        raw_items = artifact["items"] or []
        if not raw_items:
            raw_items = [{"key": "DOC", "title": artifact["title"], "text": content, "refs": []}]
        for raw in raw_items:
            key = str(raw.get("key") or "DOC")
            item_id = uuid.uuid4()
            version_id = uuid.uuid4()
            title = str(raw.get("title") or key)
            text_value = str(raw.get("text") or "")
            bind.execute(
                sa.text(
                    "INSERT INTO artifact_items "
                    "(id, project_id, artifact_id, key, type, title, text, status, "
                    "source_locator_id) VALUES "
                    "(:id, :project_id, :artifact_id, :key, :type, :title, :text, :status, :locator)"
                ),
                {
                    "id": item_id,
                    "project_id": DEFAULT_PROJECT_ID,
                    "artifact_id": artifact["id"],
                    "key": key,
                    "type": type_map[artifact["type"]],
                    "title": title,
                    "text": text_value,
                    "status": artifact["status"],
                    "locator": locator_id,
                },
            )
            bind.execute(
                sa.text(
                    "INSERT INTO item_versions "
                    "(id, item_id, version, title, text, status, source_revision_id, "
                    "source_locator_id, reason, is_active, created_by) VALUES "
                    "(:id, :item_id, 1, :title, :text, :status, :revision, :locator, "
                    "'legacy migration', true, :created_by)"
                ),
                {
                    "id": version_id,
                    "item_id": item_id,
                    "title": title,
                    "text": text_value,
                    "status": artifact["status"],
                    "revision": MANUAL_REVISION_ID,
                    "locator": locator_id,
                    "created_by": artifact["created_by"],
                },
            )
            bind.execute(
                sa.text("UPDATE artifact_items SET current_version_id = :version WHERE id = :id"),
                {"version": version_id, "id": item_id},
            )
            item_ids[(artifact["id"], key)] = item_id
            for ref in raw.get("refs", []):
                pending_refs.append(
                    (
                        item_id,
                        str(ref.get("artifact_id") or ""),
                        str(ref.get("key") or ""),
                        type_map[artifact["type"]],
                    )
                )

    inserted: set[tuple[uuid.UUID, uuid.UUID, str]] = set()
    for source_item_id, target_artifact_text, target_key, source_type in pending_refs:
        try:
            target_artifact_id = uuid.UUID(target_artifact_text)
        except ValueError:
            continue
        target_item_id = item_ids.get((target_artifact_id, target_key))
        if target_item_id is None:
            continue
        link_type = {
            "user_story": "refines",
            "task": "implements",
            "test": "tests",
        }.get(source_type, "related_to")
        identity = (source_item_id, target_item_id, link_type)
        if identity in inserted:
            continue
        inserted.add(identity)
        link_id = uuid.uuid4()
        source_locator_id = bind.execute(
            sa.text("SELECT source_locator_id FROM artifact_items WHERE id = :id"),
            {"id": source_item_id},
        ).scalar_one()
        rationale = "Migrated from artifact item reference."
        bind.execute(
            sa.text(
                "INSERT INTO item_links "
                "(id, project_id, source_item_id, target_item_id, type, origin, confidence, "
                "rationale, evidence_locator_ids, state, source_revision_id, confirmed_by, "
                "confirmed_at) VALUES "
                "(:id, :project_id, :source_id, :target_id, CAST(:type AS link_type), "
                "'imported', 1, :rationale, CAST(:evidence AS jsonb), 'confirmed', "
                ":revision, 'migration', now())"
            ),
            {
                "id": link_id,
                "project_id": DEFAULT_PROJECT_ID,
                "source_id": source_item_id,
                "target_id": target_item_id,
                "type": link_type,
                "rationale": rationale,
                "evidence": json.dumps([str(source_locator_id)]),
                "revision": MANUAL_REVISION_ID,
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO evidence_refs "
                "(id, project_id, source_locator_id, subject_type, subject_id, excerpt, digest) "
                "VALUES (:id, :project_id, :locator_id, 'item_link', :link_id, :excerpt, :digest)"
            ),
            {
                "id": uuid.uuid4(),
                "project_id": DEFAULT_PROJECT_ID,
                "locator_id": source_locator_id,
                "link_id": link_id,
                "excerpt": rationale,
                "digest": hashlib.sha256(rationale.encode()).hexdigest(),
            },
        )


def downgrade() -> None:
    op.drop_table("change_set_items")
    op.drop_table("change_sets")
    op.drop_table("context_package_items")
    op.drop_table("context_packages")
    op.drop_table("impact_candidates")
    op.drop_table("impact_analyses")
    op.drop_table("evidence_refs")
    op.drop_constraint("fk_item_current_version", "artifact_items", type_="foreignkey")
    op.drop_table("item_links")
    op.drop_table("item_versions")
    op.drop_table("artifact_items")

    op.drop_index("ix_change_logs_project_id", table_name="change_logs")
    op.drop_constraint("fk_change_logs_project", "change_logs", type_="foreignkey")
    op.drop_column("change_logs", "project_id")

    op.drop_index("ix_artifact_links_project_id", table_name="artifact_links")
    op.drop_constraint("fk_artifact_links_project", "artifact_links", type_="foreignkey")
    op.drop_column("artifact_links", "project_id")

    op.drop_index("ix_artifacts_source_locator_id", table_name="artifacts")
    op.drop_index("ix_artifacts_project_id", table_name="artifacts")
    op.drop_constraint("fk_artifacts_source_locator", "artifacts", type_="foreignkey")
    op.drop_constraint("fk_artifacts_project", "artifacts", type_="foreignkey")
    op.drop_column("artifacts", "source_locator_id")
    op.drop_column("artifacts", "project_id")

    op.drop_table("source_locators")
    op.drop_table("source_revisions")
    op.drop_table("sources")
    op.drop_table("projects")
