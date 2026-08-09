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

    # 4. Analyse without changing source knowledge, then review candidates.
    project_id = requirements["project_id"]
    analysis = client.post(
        f"/api/projects/{project_id}/impact-analyses",
        json={"query": "Users can share lists with teammates and external guests"},
    ).json()
    assert analysis["status"] == "in_review"
    assert analysis["candidates"]
    assert client.get(f"/api/artifacts/{requirements['id']}/versions").json() == versions

    for candidate in analysis["candidates"]:
        response = client.patch(
            f"/api/projects/{project_id}/impact-analyses/{analysis['id']}"
            f"/candidates/{candidate['id']}",
            json={"decision": "approved", "reviewed_by": "test"},
        )
        assert response.status_code == 200

    # 5. Produce a bounded reproducible package from approved item versions.
    package = client.post(
        f"/api/projects/{project_id}/impact-analyses/{analysis['id']}/context-packages",
        json={"token_budget": 4000},
    ).json()
    assert package["items"]
    assert package["token_estimate"] <= package["token_budget"]

    # 6. The scoped consistency report stays clean.
    report = client.get(f"/api/projects/{project_id}/consistency").json()
    assert report["errors"] == 0
