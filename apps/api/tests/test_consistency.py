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
