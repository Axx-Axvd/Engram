"""Read-only GitHub source import and causal ChangeSet coverage."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from engram.models import ChangeSet, ChangeSetItem, SourceRevision
from engram.services import github_source_service


class FakeGitHubClient:
    def json(self, path: str, *, params: dict | None = None):
        if "/commits/" in path:
            sha = "def456" if path.endswith("/next") else "abc123"
            return {
                "sha": sha,
                "html_url": f"https://github.test/acme/repo/commit/{sha}",
                "commit": {
                    "message": (
                        "docs: replace implementation"
                        if sha == "def456"
                        else "feat: invitation flow"
                    ),
                    "author": {"date": "2026-08-01T00:00:00Z"},
                },
            }
        if "/git/trees/" in path:
            if path.endswith("/def456"):
                return {
                    "truncated": False,
                    "tree": [{"type": "blob", "path": "README.md", "size": 100}],
                }
            return {
                "truncated": False,
                "tree": [
                    {"type": "blob", "path": "README.md", "size": 100},
                    {"type": "blob", "path": "src/invitations.py", "size": 100},
                    {"type": "blob", "path": "tests/test_invitations.py", "size": 100},
                ],
            }
        if path.endswith("/issues"):
            return [
                {
                    "number": 7,
                    "title": "Invite external guests",
                    "body": "Guests receive an email invitation.",
                    "html_url": "https://github.test/acme/repo/issues/7",
                },
                {
                    "number": 9,
                    "title": "Implement invitations",
                    "body": "Adds the invitation flow.",
                    "html_url": "https://github.test/acme/repo/pull/9",
                    "pull_request": {},
                },
            ]
        raise AssertionError(f"Unexpected JSON request: {path} {params}")

    def text(self, path: str, *, params: dict | None = None) -> str:
        if path.endswith("README.md"):
            suffix = (
                " Invitations are now documented."
                if params and params.get("ref") == "def456"
                else ""
            )
            return f"# Product\n\n## Invitations\nGuests receive invitations.{suffix}"
        if path.endswith("src/invitations.py"):
            return "def invite_guest(email: str) -> None:\n    pass\n"
        if path.endswith("tests/test_invitations.py"):
            return "def test_invite_guest():\n    assert True\n"
        raise AssertionError(f"Unexpected text request: {path} {params}")


def test_github_sync_imports_fixed_revision_and_changeset(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    project = client.post("/api/projects", json={"name": "GitHub project"}).json()
    source_response = client.post(
        f"/api/projects/{project['id']}/sources/github",
        json={"repository": "acme/repo", "ref": "main"},
    )
    assert source_response.status_code == 201, source_response.text
    source = source_response.json()
    monkeypatch.setattr(github_source_service, "GitHubClient", lambda: FakeGitHubClient())

    response = client.post(
        f"/api/projects/{project['id']}/sources/{source['id']}/sync",
        json={"ref": "main", "created_by": "test"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["revision"]["revision"] == "abc123"
    assert result["imported_items"] >= 6
    assert result["change_set_id"]

    items = client.get(f"/api/projects/{project['id']}/items").json()
    assert {value["type"] for value in items} >= {
        "document",
        "code_component",
        "test",
        "commit",
        "issue",
        "pull_request",
    }
    assert all(value["source_locator_id"] for value in items)

    change_set = db_session.scalar(select(ChangeSet).where(ChangeSet.id == result["change_set_id"]))
    assert change_set is not None
    assert change_set.external_id == "abc123"
    assert db_session.scalars(
        select(ChangeSetItem).where(ChangeSetItem.change_set_id == change_set.id)
    ).all()
    api_change_sets = client.get(f"/api/projects/{project['id']}/change-sets")
    assert api_change_sets.status_code == 200, api_change_sets.text
    assert api_change_sets.json()[0]["id"] == result["change_set_id"]
    assert api_change_sets.json()[0]["items"]

    analysis_response = client.post(
        f"/api/projects/{project['id']}/impact-analyses",
        json={"query": "Change how external guests receive invitations"},
    )
    assert analysis_response.status_code == 201, analysis_response.text
    analysis = analysis_response.json()
    assert analysis["candidates"]
    for candidate in analysis["candidates"]:
        review = client.patch(
            f"/api/projects/{project['id']}/impact-analyses/{analysis['id']}"
            f"/candidates/{candidate['id']}",
            json={"decision": "approved", "reviewed_by": "test"},
        )
        assert review.status_code == 200
    package = client.post(
        f"/api/projects/{project['id']}/impact-analyses/{analysis['id']}/context-packages",
        json={"token_budget": 4000, "created_by": "test"},
    )
    assert package.status_code == 201, package.text
    assert package.json()["token_estimate"] <= package.json()["token_budget"]

    repeated = client.post(
        f"/api/projects/{project['id']}/sources/{source['id']}/sync",
        json={"ref": "main"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["imported_items"] == 0
    assert (
        len(
            db_session.scalars(
                select(SourceRevision).where(SourceRevision.source_id == source["id"])
            ).all()
        )
        == 1
    )

    next_revision = client.post(
        f"/api/projects/{project['id']}/sources/{source['id']}/sync",
        json={"ref": "next", "analysis_id": analysis["id"]},
    )
    assert next_revision.status_code == 200, next_revision.text
    assert next_revision.json()["revision"]["revision"] == "def456"
    assert next_revision.json()["deleted_items"] >= 3
    active_types = {
        value["type"] for value in client.get(f"/api/projects/{project['id']}/items").json()
    }
    assert "code_component" not in active_types
    assert "test" not in active_types
    latest_change_set = client.get(f"/api/projects/{project['id']}/change-sets").json()[0]
    assert latest_change_set["analysis_id"] == analysis["id"]
    assert any(value["change_kind"] == "deleted" for value in latest_change_set["items"])
    consistency = client.get(f"/api/projects/{project['id']}/consistency")
    assert consistency.status_code == 200


def test_change_set_records_exact_versions_and_never_adopts_a_foreign_analysis(
    client: TestClient, monkeypatch
) -> None:
    project = client.post("/api/projects", json={"name": "Causal ChangeSet"}).json()
    source = client.post(
        f"/api/projects/{project['id']}/sources/github",
        json={"repository": "acme/repo", "ref": "main"},
    ).json()
    monkeypatch.setattr(github_source_service, "GitHubClient", lambda: FakeGitHubClient())

    first = client.post(
        f"/api/projects/{project['id']}/sources/{source['id']}/sync",
        json={"ref": "main", "created_by": "test"},
    )
    assert first.status_code == 200, first.text

    items = client.get(f"/api/projects/{project['id']}/items").json()
    by_path = {value["title"].split(" · ", 1)[0]: value for value in items}
    change_set = client.get(
        f"/api/projects/{project['id']}/change-sets/{first.json()['change_set_id']}"
    ).json()
    recorded = {value["item_id"]: value for value in change_set["items"]}

    # The changed code file and the test covering it belong to the same causal ChangeSet.
    assert by_path["src/invitations.py"]["id"] in recorded
    assert by_path["tests/test_invitations.py"]["id"] in recorded
    for item in items:
        entry = recorded.get(item["id"])
        assert entry is not None, item["title"]
        # A first import creates the element, so it has no predecessor and points at
        # exactly the version that is active now.
        assert entry["before_version_id"] is None
        assert entry["after_version_id"] == item["current_version_id"]
        assert entry["change_kind"] == "added"

    # An analysis opened after that import was not caused by it.
    analysis = client.post(
        f"/api/projects/{project['id']}/impact-analyses",
        json={"query": "Change how external guests receive invitations"},
    )
    assert analysis.status_code == 201, analysis.text
    unrelated = client.post(
        f"/api/projects/{project['id']}/sources/{source['id']}/sync",
        json={"ref": "next", "created_by": "test"},
    )
    assert unrelated.status_code == 200, unrelated.text
    change_sets = client.get(f"/api/projects/{project['id']}/change-sets").json()
    assert len(change_sets) == 2
    assert all(value["analysis_id"] is None for value in change_sets)
    still_open = client.get(
        f"/api/projects/{project['id']}/impact-analyses/{analysis.json()['id']}"
    ).json()
    assert still_open["status"] != "applied"
