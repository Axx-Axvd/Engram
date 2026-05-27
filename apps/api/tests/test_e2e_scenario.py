"""End-to-end scenario covering the MVP definition of done, through the public API."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_full_scenario(client: TestClient) -> None:
    # 1. Accept a project description and formalize it into grouped documents.
    formalized = client.post(
        "/api/workflows/formalize",
        json={"description": "Users can create tasks. Users can share lists with teammates."},
    ).json()
    types = {a["type"] for a in formalized["artifacts"]}
    assert types == {"project_brief", "requirement", "user_story", "task", "test_case"}

    requirements = next(a for a in formalized["artifacts"] if a["type"] == "requirement")
    assert requirements["items"], "requirements document should carry items"

    # 2. Browse the produced artifacts.
    listing = client.get("/api/artifacts", params={"limit": 500}).json()
    assert len(listing) == 5

    # 3. Each document starts at one active version.
    versions = client.get(f"/api/artifacts/{requirements['id']}/versions").json()
    assert len(versions) == 1
    assert versions[0]["is_active"] is True

    # 4. A change request finds impact, writes new versions, and links them.
    impact = client.post(
        "/api/workflows/change-request",
        json={"text": "Users can share lists with teammates and external guests"},
    ).json()
    assert impact["change_request"]["status"] == "applied"
    assert impact["impacted"], "the change should impact at least one document"
    assert all(item["artifact"]["current_version"] >= 2 for item in impact["impacted"])
    assert impact["links"] and all(link["type"] == "changes" for link in impact["links"])

    # 5. The consistency report stays clean (coverage intact, change request touched artifacts).
    report = client.get("/api/consistency").json()
    assert report["errors"] == 0
