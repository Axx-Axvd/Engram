from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def test_formalized_project_is_consistent(client: TestClient) -> None:
    client.post(
        "/api/workflows/formalize",
        json={"description": "Users can create tasks. Users can share lists with teammates."},
    )
    report = client.get("/api/consistency").json()
    assert report["ok"] is True
    assert report["errors"] == 0
    assert report["warnings"] == 0
    assert report["checked_artifacts"] == 5


def test_uncovered_requirement_warns(client: TestClient) -> None:
    client.post(
        "/api/artifacts",
        json={
            "type": "requirement",
            "title": "Requirements",
            "items": [{"key": "R1", "title": "Login", "text": "Users can log in"}],
        },
    )
    report = client.get("/api/consistency").json()
    assert report["ok"] is True  # only warnings, no errors
    assert report["errors"] == 0
    codes = {issue["code"] for issue in report["issues"]}
    assert "requirement_without_task" in codes
    assert "requirement_without_test" in codes


def test_dangling_reference_errors(client: TestClient) -> None:
    ghost = str(uuid.uuid4())
    client.post(
        "/api/artifacts",
        json={
            "type": "task",
            "title": "Tasks",
            "items": [
                {"key": "T1", "title": "Do it", "refs": [{"artifact_id": ghost, "key": "R1"}]}
            ],
        },
    )
    report = client.get("/api/consistency").json()
    assert report["ok"] is False
    assert report["errors"] >= 1
    assert any(issue["code"] == "dangling_reference" for issue in report["issues"])


def test_change_request_without_impact_errors(client: TestClient) -> None:
    client.post("/api/artifacts", json={"type": "change_request", "title": "CR", "content": "do x"})
    report = client.get("/api/consistency").json()
    assert report["ok"] is False
    assert any(issue["code"] == "change_request_without_impact" for issue in report["issues"])


def test_approved_requirement_without_source_errors(client: TestClient) -> None:
    client.post(
        "/api/artifacts",
        json={
            "type": "requirement",
            "title": "Requirements",
            "status": "approved",
            "items": [{"key": "R1", "title": "Login", "text": "Users can log in"}],
        },
    )
    report = client.get("/api/consistency").json()
    assert report["ok"] is False
    assert any(i["code"] == "approved_requirement_without_source" for i in report["issues"])


def test_requirement_without_user_story_warns(client: TestClient) -> None:
    req = client.post(
        "/api/artifacts",
        json={
            "type": "requirement",
            "title": "Requirements",
            "items": [{"key": "R1", "title": "Login", "text": "log in"}],
        },
    ).json()
    ref = {"artifact_id": req["id"], "key": "R1"}
    client.post(
        "/api/artifacts",
        json={
            "type": "task",
            "title": "Tasks",
            "items": [{"key": "T1", "title": "do", "refs": [ref]}],
        },
    )
    client.post(
        "/api/artifacts",
        json={
            "type": "test_case",
            "title": "Test cases",
            "items": [{"key": "TC1", "title": "verify", "refs": [ref]}],
        },
    )
    report = client.get("/api/consistency").json()
    codes = {i["code"] for i in report["issues"]}
    assert report["ok"] is True  # warnings only, no errors
    assert "requirement_without_user_story" in codes
    assert "requirement_without_task" not in codes
    assert "requirement_without_test" not in codes


def test_handauthored_user_story_without_requirement_warns(client: TestClient) -> None:
    # A user story authored by hand (no items, no links) must still be flagged (spec §10.1.2).
    client.post(
        "/api/artifacts",
        json={"type": "user_story", "title": "Тестовая дока", "content": "as a user…"},
    )
    report = client.get("/api/consistency").json()
    assert report["ok"] is True  # warning only
    assert any(i["code"] == "user_story_without_requirement" for i in report["issues"])


def test_user_story_traces_via_document_link(client: TestClient) -> None:
    req = client.post(
        "/api/artifacts",
        json={
            "type": "requirement",
            "title": "Requirements",
            "items": [{"key": "R1", "title": "Login", "text": "log in"}],
        },
    ).json()
    story = client.post(
        "/api/artifacts",
        json={"type": "user_story", "title": "Тестовая дока", "content": "as a user…"},
    ).json()
    client.post(
        "/api/links",
        json={"source_id": story["id"], "target_id": req["id"], "type": "refines"},
    )
    report = client.get("/api/consistency").json()
    assert not any(i["code"] == "user_story_without_requirement" for i in report["issues"])


def test_archived_used_as_active_warns(client: TestClient) -> None:
    req = client.post(
        "/api/artifacts",
        json={
            "type": "requirement",
            "title": "Requirements",
            "status": "archived",
            "items": [{"key": "R1", "title": "Login", "text": "log in"}],
        },
    ).json()
    client.post(
        "/api/artifacts",
        json={
            "type": "task",
            "title": "Tasks",
            "items": [
                {"key": "T1", "title": "do", "refs": [{"artifact_id": req["id"], "key": "R1"}]}
            ],
        },
    )
    report = client.get("/api/consistency").json()
    assert any(i["code"] == "archived_used_as_active" for i in report["issues"])


def test_approved_cr_without_new_version(client: TestClient) -> None:
    cr = client.post(
        "/api/artifacts",
        json={"type": "change_request", "title": "CR", "content": "do x", "status": "approved"},
    ).json()
    target = client.post(
        "/api/artifacts",
        json={
            "type": "requirement",
            "title": "Requirements",
            "items": [{"key": "R1", "title": "Login", "text": "log in"}],
        },
    ).json()
    client.post(
        "/api/links",
        json={"source_id": cr["id"], "target_id": target["id"], "type": "changes"},
    )

    report = client.get("/api/consistency").json()
    assert report["ok"] is False
    assert any(i["code"] == "approved_cr_without_new_version" for i in report["issues"])

    # Revising the linked artifact (a new version) clears the rule.
    client.patch(f"/api/artifacts/{target['id']}", json={"content": "revised", "reason": "cr"})
    cleared = client.get("/api/consistency").json()
    assert not any(i["code"] == "approved_cr_without_new_version" for i in cleared["issues"])
