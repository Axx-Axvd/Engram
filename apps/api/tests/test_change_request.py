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


def test_change_request_creates_impact_and_versions(client: TestClient) -> None:
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
    assert cr["status"] == "applied"

    assert len(data["impacted"]) >= 1
    assert data["summary"]

    # One changes-link per impacted artifact, all originating from the change request.
    assert len(data["links"]) == len(data["impacted"])
    for link in data["links"]:
        assert link["type"] == "changes"
        assert link["source_id"] == cr["id"]

    # Every impacted artifact received a new version and a rationale.
    for item in data["impacted"]:
        assert item["artifact"]["current_version"] >= 2
        assert item["rationale"]


def test_change_request_links_visible_on_impacted_artifact(client: TestClient) -> None:
    _seed(client)
    data = client.post(
        "/api/workflows/change-request",
        json={"text": "Users can share lists with teammates"},
    ).json()

    assert data["impacted"], "expected at least one impacted artifact"
    target_id = data["impacted"][0]["artifact"]["id"]

    links = client.get(f"/api/artifacts/{target_id}/links").json()
    assert any(link["type"] == "changes" and link["target_id"] == target_id for link in links)
