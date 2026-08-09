from __future__ import annotations

from fastapi.testclient import TestClient


def _seed(client: TestClient) -> None:
    client.post(
        "/api/workflows/formalize",
        json={
            "description": (
                "Users can create tasks with a due date. Users can share lists with teammates."
            )
        },
    )


def test_change_request_creates_review_without_mutating_versions(client: TestClient) -> None:
    _seed(client)

    resp = client.post(
        "/api/workflows/change-request",
        json={
            "text": "Users can share lists with teammates and external guests",
            "max_impacted": 5,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    cr = data["change_request"]
    assert cr["type"] == "change_request"
    assert cr["status"] == "in_review"

    assert len(data["impacted"]) >= 1
    assert data["summary"]

    # Analysis is a proposal: no causal link or source version is created yet.
    assert data["links"] == []

    # Every impacted artifact stays at its original version and has a rationale.
    for item in data["impacted"]:
        assert item["artifact"]["current_version"] == 1
        assert item["rationale"]


def test_change_request_is_stored_as_impact_analysis(client: TestClient) -> None:
    _seed(client)
    data = client.post(
        "/api/workflows/change-request",
        json={"text": "Users can share lists with teammates"},
    ).json()

    assert data["impacted"], "expected at least one impacted artifact"
    project_id = data["change_request"]["project_id"]
    analyses = client.get(f"/api/projects/{project_id}/impact-analyses").json()
    assert len(analyses) == 1
    assert analyses[0]["status"] == "in_review"
    assert analyses[0]["candidates"]
