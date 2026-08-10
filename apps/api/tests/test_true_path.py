"""Acceptance tests for project isolation, safe impact analysis and context packages."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from engram.llm import ImpactAnalysisResult, ImpactProposal
from engram.services import analysis_service


def _project(client: TestClient, name: str) -> dict:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def _requirement(client: TestClient, project_id: str, title: str, key: str = "R1") -> dict:
    response = client.post(
        f"/api/projects/{project_id}/artifacts",
        json={
            "type": "requirement",
            "title": title,
            "content": title,
            "items": [{"key": key, "title": title, "text": title}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_projects_isolate_artifacts_search_links_and_consistency(client: TestClient) -> None:
    first = _project(client, "First")
    second = _project(client, "Second")
    first_artifact = _requirement(client, first["id"], "Alpha checkout requirement")
    second_artifact = _requirement(client, second["id"], "Beta profile requirement")

    first_listing = client.get(f"/api/projects/{first['id']}/artifacts").json()
    second_listing = client.get(f"/api/projects/{second['id']}/artifacts").json()
    assert {value["id"] for value in first_listing} == {first_artifact["id"]}
    assert {value["id"] for value in second_listing} == {second_artifact["id"]}

    bundle = client.post(
        f"/api/projects/{first['id']}/search/context",
        json={"query": "profile", "hops": 0},
    ).json()
    assert second_artifact["id"] not in {value["id"] for value in bundle["artifacts"]}

    cross_link = client.post(
        f"/api/projects/{first['id']}/links",
        json={
            "source_id": first_artifact["id"],
            "target_id": second_artifact["id"],
            "type": "related_to",
        },
    )
    assert cross_link.status_code == 422

    first_report = client.get(f"/api/projects/{first['id']}/consistency").json()
    second_report = client.get(f"/api/projects/{second['id']}/consistency").json()
    assert first_report["checked_artifacts"] == 1
    assert second_report["checked_artifacts"] == 1


def test_artifact_items_are_normalized_versioned_and_provenanced(client: TestClient) -> None:
    project = _project(client, "Knowledge")
    artifact = _requirement(client, project["id"], "Users can export reports")
    assert artifact["source_locator_id"]

    items = client.get(f"/api/projects/{project['id']}/items").json()
    assert len(items) == 1
    assert items[0]["key"] == "R1"
    assert items[0]["source_locator_id"] == artifact["source_locator_id"]
    versions = client.get(f"/api/projects/{project['id']}/items/{items[0]['id']}/versions").json()
    assert len(versions) == 1
    assert versions[0]["source_revision_id"]
    assert versions[0]["is_active"] is True

    update = client.patch(
        f"/api/projects/{project['id']}/artifacts/{artifact['id']}",
        json={"content": "Users can export reports as CSV", "updated_by": "editor"},
    )
    assert update.status_code == 200, update.text
    assert update.json()["source_locator_id"] != artifact["source_locator_id"]
    versions = client.get(f"/api/projects/{project['id']}/items/{items[0]['id']}/versions").json()
    assert len(versions) == 2
    assert versions[0]["source_revision_id"] != versions[1]["source_revision_id"]

    direct_update = client.patch(
        f"/api/projects/{project['id']}/items/{items[0]['id']}",
        json={"text": "Users can export reports as CSV or JSON", "updated_by": "reviewer"},
    )
    assert direct_update.status_code == 200, direct_update.text
    direct_versions = client.get(
        f"/api/projects/{project['id']}/items/{items[0]['id']}/versions"
    ).json()
    assert len(direct_versions) == 3
    assert len({value["source_revision_id"] for value in direct_versions}) == 3


def test_item_container_locator_and_link_revision_cannot_cross_projects(
    client: TestClient,
) -> None:
    first = _project(client, "Boundary one")
    second = _project(client, "Boundary two")
    first_artifact = _requirement(client, first["id"], "First requirement", key="R1")
    second_artifact = _requirement(client, second["id"], "Second requirement", key="R2")
    first_items = client.get(f"/api/projects/{first['id']}/items").json()
    second_items = client.get(f"/api/projects/{second['id']}/items").json()

    invalid_container = client.post(
        f"/api/projects/{first['id']}/items",
        json={
            "artifact_id": second_artifact["id"],
            "key": "ROGUE",
            "type": "requirement",
            "title": "Cross-project item",
            "source_locator_id": first_items[0]["source_locator_id"],
        },
    )
    assert invalid_container.status_code == 422

    extra = _requirement(client, first["id"], "Another first requirement", key="R3")
    assert extra["project_id"] == first_artifact["project_id"]
    first_items = client.get(f"/api/projects/{first['id']}/items").json()
    second_versions = client.get(
        f"/api/projects/{second['id']}/items/{second_items[0]['id']}/versions"
    ).json()
    invalid_revision = client.post(
        f"/api/projects/{first['id']}/item-links",
        json={
            "source_item_id": first_items[0]["id"],
            "target_item_id": first_items[1]["id"],
            "type": "related_to",
            "source_revision_id": second_versions[0]["source_revision_id"],
        },
    )
    assert invalid_revision.status_code == 422


def test_item_link_type_matrix_and_inferred_review_are_enforced(client: TestClient) -> None:
    project = _project(client, "Links")
    _requirement(client, project["id"], "Payment requirement")
    response = client.post(
        f"/api/projects/{project['id']}/artifacts",
        json={
            "type": "test_case",
            "title": "Payment test",
            "items": [{"key": "TC1", "title": "Payment test", "text": "Verify payment"}],
        },
    )
    assert response.status_code == 201
    items = client.get(f"/api/projects/{project['id']}/items").json()
    requirement = next(value for value in items if value["type"] == "requirement")
    test = next(value for value in items if value["type"] == "test")

    invalid = client.post(
        f"/api/projects/{project['id']}/item-links",
        json={
            "source_item_id": requirement["id"],
            "target_item_id": test["id"],
            "type": "tests",
        },
    )
    assert invalid.status_code == 422

    inferred = client.post(
        f"/api/projects/{project['id']}/item-links",
        json={
            "source_item_id": test["id"],
            "target_item_id": requirement["id"],
            "type": "tests",
            "origin": "inferred",
            "state": "confirmed",
        },
    )
    assert inferred.status_code == 422

    accepted = client.post(
        f"/api/projects/{project['id']}/item-links",
        json={
            "source_item_id": test["id"],
            "target_item_id": requirement["id"],
            "type": "tests",
            "origin": "inferred",
            "state": "proposed",
            "confidence": 0.7,
            "rationale": "Matching payment behavior",
        },
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["state"] == "proposed"
    assert accepted.json()["evidence_locator_ids"] == [test["source_locator_id"]]
    reviewed = client.patch(
        f"/api/projects/{project['id']}/item-links/{accepted.json()['id']}",
        json={"state": "confirmed", "reviewed_by": "reviewer"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["state"] == "confirmed"
    assert reviewed.json()["confirmed_by"] == "reviewer"

    update = client.patch(
        f"/api/projects/{project['id']}/items/{test['id']}",
        json={"text": "Verify the revised payment behavior", "updated_by": "reviewer"},
    )
    assert update.status_code == 200
    links = client.get(f"/api/projects/{project['id']}/item-links").json()
    assert links[0]["state"] == "stale"
    report = client.get(f"/api/projects/{project['id']}/consistency").json()
    assert any(issue["code"] == "stale_item_link" for issue in report["issues"])


def test_impact_analysis_is_non_mutating_and_package_is_budgeted(client: TestClient) -> None:
    project = _project(client, "Impact")
    artifact = _requirement(client, project["id"], "Guests can receive email invitations")
    before = client.get(f"/api/artifacts/{artifact['id']}/versions").json()

    response = client.post(
        f"/api/projects/{project['id']}/impact-analyses",
        json={"query": "Allow external guests to receive email invitations", "context_budget": 512},
    )
    assert response.status_code == 201, response.text
    analysis = response.json()
    assert analysis["candidates"]
    assert all(value["evidence"] for value in analysis["candidates"])
    assert client.get(f"/api/artifacts/{artifact['id']}/versions").json() == before

    for candidate in analysis["candidates"]:
        review = client.patch(
            f"/api/projects/{project['id']}/impact-analyses/{analysis['id']}"
            f"/candidates/{candidate['id']}",
            json={"decision": "approved", "reviewed_by": "reviewer"},
        )
        assert review.status_code == 200

    package_response = client.post(
        f"/api/projects/{project['id']}/impact-analyses/{analysis['id']}/context-packages",
        json={"token_budget": 512},
    )
    assert package_response.status_code == 201, package_response.text
    package = package_response.json()
    assert package["items"]
    assert package["token_estimate"] <= 512
    assert all(value["version"]["is_active"] for value in package["items"])
    assert all(value["source_locator"]["content_hash"] for value in package["items"])
    packages = client.get(f"/api/projects/{project['id']}/context-packages")
    assert packages.status_code == 200
    assert [value["id"] for value in packages.json()] == [package["id"]]


def test_research_retrieval_modes_are_recorded_and_non_mutating(client: TestClient) -> None:
    project = _project(client, "Retrieval modes")
    artifact = _requirement(client, project["id"], "Guests receive email invitations")
    before = client.get(f"/api/artifacts/{artifact['id']}/versions").json()

    for mode in ("full", "vector", "graph", "combined"):
        response = client.post(
            f"/api/projects/{project['id']}/impact-analyses",
            json={
                "query": "Guests receive email invitations",
                "retrieval_mode": mode,
                "context_budget": 10000,
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["retrieval_mode"] == mode
        assert response.json()["algorithm_version"] == f"impact-v1:{mode}"

    assert client.get(f"/api/artifacts/{artifact['id']}/versions").json() == before


def test_invalid_model_result_is_rejected_atomically(client: TestClient, monkeypatch) -> None:
    project = _project(client, "Invalid model")
    _requirement(client, project["id"], "Users can log in")

    class InvalidProvider:
        def analyze_impact(self, change_text, context):
            return ImpactAnalysisResult(
                summary="invalid",
                proposals=[
                    ImpactProposal(
                        item_id=str(uuid.uuid4()),
                        item_version_id=str(uuid.uuid4()),
                        impact_type="modify",
                        confidence=0.9,
                        rationale="invented",
                        evidence=["invented"],
                        proposed_action="invented",
                    )
                ],
            )

    monkeypatch.setattr(analysis_service, "get_llm_provider", lambda: InvalidProvider())
    response = client.post(
        f"/api/projects/{project['id']}/impact-analyses",
        json={"query": "Users can log in with a changed flow"},
    )
    assert response.status_code == 422
    assert client.get(f"/api/projects/{project['id']}/impact-analyses").json() == []


def test_malformed_model_classification_is_rejected_atomically(
    client: TestClient, monkeypatch
) -> None:
    project = _project(client, "Malformed model")
    _requirement(client, project["id"], "Users can log in")

    class InvalidProvider:
        def analyze_impact(self, change_text, context):
            element = context[0]
            evidence = str(element.source_locator["id"])
            return ImpactAnalysisResult(
                summary="invalid",
                proposals=[
                    ImpactProposal(
                        item_id=element.id,
                        item_version_id=element.item_version_id,
                        impact_type="invented",
                        confidence=2.0,
                        rationale="invalid classification",
                        evidence=[evidence],
                        proposed_action="review",
                    )
                ],
            )

    monkeypatch.setattr(analysis_service, "get_llm_provider", lambda: InvalidProvider())
    response = client.post(
        f"/api/projects/{project['id']}/impact-analyses",
        json={"query": "Users can log in with a changed flow"},
    )
    assert response.status_code == 422
    assert client.get(f"/api/projects/{project['id']}/impact-analyses").json() == []


def test_editing_one_item_leaves_siblings_and_container_untouched(client: TestClient) -> None:
    project = _project(client, "Targeted impact")
    response = client.post(
        f"/api/projects/{project['id']}/artifacts",
        json={
            "type": "requirement",
            "title": "Checkout requirements",
            "content": "Checkout requirements",
            "items": [
                {"key": "R1", "title": "Guests pay by card", "text": "Guests pay by card"},
                {"key": "R2", "title": "Guests pay by invoice", "text": "Guests pay by invoice"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    artifact = response.json()
    listed = client.get(f"/api/projects/{project['id']}/items").json()
    items = {value["key"]: value for value in listed}
    assert set(items) == {"R1", "R2"}
    artifact_versions = client.get(f"/api/artifacts/{artifact['id']}/versions").json()
    sibling_version_id = items["R2"]["current_version_id"]

    update = client.patch(
        f"/api/projects/{project['id']}/items/{items['R1']['id']}",
        json={"text": "Guests pay by card or wallet", "updated_by": "reviewer"},
    )
    assert update.status_code == 200, update.text

    edited = client.get(f"/api/projects/{project['id']}/items/{items['R1']['id']}/versions").json()
    sibling = client.get(f"/api/projects/{project['id']}/items/{items['R2']['id']}/versions").json()
    assert len(edited) == 2
    assert len(sibling) == 1
    sibling_now = client.get(f"/api/projects/{project['id']}/items/{items['R2']['id']}").json()
    assert sibling_now["current_version_id"] == sibling_version_id
    # The container document is not rewritten because one of its items changed.
    assert client.get(f"/api/artifacts/{artifact['id']}/versions").json() == artifact_versions


def test_every_context_package_item_states_why_it_was_included(client: TestClient) -> None:
    project = _project(client, "Explainability")
    _requirement(client, project["id"], "Guests can receive email invitations")

    created = client.post(
        f"/api/projects/{project['id']}/impact-analyses",
        json={"query": "Allow external guests to receive email invitations"},
    )
    assert created.status_code == 201, created.text
    analysis = created.json()
    for candidate in analysis["candidates"]:
        review = client.patch(
            f"/api/projects/{project['id']}/impact-analyses/{analysis['id']}"
            f"/candidates/{candidate['id']}",
            json={"decision": "approved", "reviewed_by": "reviewer"},
        )
        assert review.status_code == 200

    package = client.post(
        f"/api/projects/{project['id']}/impact-analyses/{analysis['id']}/context-packages",
        json={"token_budget": 4000},
    )
    assert package.status_code == 201, package.text
    entries = package.json()["items"]
    assert entries
    assert [entry["rank"] for entry in entries] == list(range(1, len(entries) + 1))
    for entry in entries:
        reason = entry["reason"]
        assert reason["impact_type"]
        assert reason["rationale"]
        assert reason["evidence"]
        selection = reason["selection"]
        if selection["stage"] == "graph_expansion":
            assert selection["link_id"] and selection["link_type"]
            assert entry["graph_path"]
        else:
            assert selection["stage"] == "retrieval"
            assert selection["retrieval_mode"]
            assert (
                selection["matched_terms"]
                or selection["vector_score"] > 0
                or selection["explicit_key"]
            )
        assert entry["token_estimate"] >= 1
        assert entry["source_locator"]["content_hash"]
