"""The agent-facing MCP channel: bounded packages, and no way around human review."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from engram.errors import NotFoundError, ValidationError
from engram.mcp import operations


def _project_with_knowledge(client: TestClient, name: str) -> dict:
    project = client.post("/api/projects", json={"name": name}).json()
    response = client.post(
        f"/api/projects/{project['id']}/artifacts",
        json={
            "type": "requirement",
            "title": "Guests can receive email invitations",
            "content": "Guests can receive email invitations",
            "items": [
                {
                    "key": "R1",
                    "title": "Guests can receive email invitations",
                    "text": "Guests can receive email invitations",
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return project


def test_analyze_change_reports_evidence_without_mutating_knowledge(
    client: TestClient, db_session: Session
) -> None:
    project = _project_with_knowledge(client, "MCP analyze")
    versions_before = client.get(f"/api/projects/{project['id']}/items").json()

    result = operations.analyze_change(
        db_session,
        project_id=uuid.UUID(project["id"]),
        query="Allow external guests to receive email invitations",
    )
    db_session.commit()

    assert result["candidates"]
    assert result["status"] == "in_review"
    assert result["retrieval_mode"] == "combined"
    for candidate in result["candidates"]:
        assert candidate["review_decision"] == "pending"
        assert candidate["evidence"]
        assert candidate["selection_reason"]["stage"] in {"retrieval", "graph_expansion"}
    # The agent is told review is required rather than left to assume the result is applied.
    assert "human" in result["next_step"].lower()
    assert client.get(f"/api/projects/{project['id']}/items").json() == versions_before


def test_get_context_refuses_until_a_human_approves(
    client: TestClient, db_session: Session
) -> None:
    project = _project_with_knowledge(client, "MCP review gate")
    analysis = operations.analyze_change(
        db_session,
        project_id=uuid.UUID(project["id"]),
        query="Allow external guests to receive email invitations",
    )
    db_session.commit()

    with pytest.raises(ValidationError):
        operations.get_context(
            db_session,
            project_id=uuid.UUID(project["id"]),
            analysis_id=uuid.UUID(analysis["analysis_id"]),
        )
    db_session.rollback()
    assert operations.list_context_packages(
        db_session, project_id=uuid.UUID(project["id"])
    ) == []


def test_approved_analysis_yields_a_bounded_explained_package(
    client: TestClient, db_session: Session
) -> None:
    project = _project_with_knowledge(client, "MCP package")
    analysis = operations.analyze_change(
        db_session,
        project_id=uuid.UUID(project["id"]),
        query="Allow external guests to receive email invitations",
    )
    db_session.commit()

    for candidate in analysis["candidates"]:
        review = client.patch(
            f"/api/projects/{project['id']}/impact-analyses/{analysis['analysis_id']}"
            f"/candidates/{candidate['candidate_id']}",
            json={"decision": "approved", "reviewed_by": "reviewer"},
        )
        assert review.status_code == 200, review.text

    package = operations.get_context(
        db_session,
        project_id=uuid.UUID(project["id"]),
        analysis_id=uuid.UUID(analysis["analysis_id"]),
        budget=600,
    )
    db_session.commit()

    assert package["items"]
    assert package["token_estimate"] <= 600
    assert package["token_budget"] == 600
    for entry in package["items"]:
        assert entry["item_version_id"]
        assert entry["source"]["content_hash"]
        assert entry["reason"]["impact_type"]
        assert entry["reason"]["evidence"]

    listed = operations.list_context_packages(db_session, project_id=uuid.UUID(project["id"]))
    assert [value["package_id"] for value in listed] == [package["package_id"]]

    # The package is a snapshot: fetching it again returns the same pinned versions.
    again = client.get(
        f"/api/projects/{project['id']}/context-packages/{package['package_id']}"
    ).json()
    assert [entry["version"]["id"] for entry in again["items"]] == [
        entry["item_version_id"] for entry in package["items"]
    ]


def test_channel_cannot_reach_another_project(client: TestClient, db_session: Session) -> None:
    first = _project_with_knowledge(client, "MCP boundary one")
    second = _project_with_knowledge(client, "MCP boundary two")
    analysis = operations.analyze_change(
        db_session,
        project_id=uuid.UUID(first["id"]),
        query="Allow external guests to receive email invitations",
    )
    db_session.commit()

    with pytest.raises(NotFoundError):
        operations.get_context(
            db_session,
            project_id=uuid.UUID(second["id"]),
            analysis_id=uuid.UUID(analysis["analysis_id"]),
        )
    db_session.rollback()

    listed = {value["project_id"] for value in operations.list_projects(db_session)}
    assert {first["id"], second["id"]} <= listed
