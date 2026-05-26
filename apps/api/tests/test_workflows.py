from __future__ import annotations

from fastapi.testclient import TestClient


def _formalize(client: TestClient, description: str) -> dict:
    resp = client.post("/api/workflows/formalize", json={"description": description})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_formalize_single_requirement_counts(client: TestClient) -> None:
    data = _formalize(client, "Users can create and delete tasks")
    arts = data["artifacts"]
    links = data["links"]

    by_type = lambda t: sum(a["type"] == t for a in arts)  # noqa: E731
    assert by_type("requirement") == 1
    assert by_type("test_case") == 1
    assert by_type("user_story") == 1
    assert by_type("task") == 2
    assert len(arts) == 5
    assert len(links) == 4
    assert {link["type"] for link in links} == {"tests", "refines", "implements"}


def test_formalize_builds_connected_graph(client: TestClient) -> None:
    desc = "Users can create tasks. Users can complete tasks. Users group tasks into lists."
    data = _formalize(client, desc)
    arts = {a["id"]: a for a in data["artifacts"]}

    assert sum(a["type"] == "requirement" for a in arts.values()) == 3

    # Every link connects two artifacts that are part of the produced graph.
    for link in data["links"]:
        assert link["source_id"] in arts
        assert link["target_id"] in arts

    # Each user story refines a requirement.
    refines = [link for link in data["links"] if link["type"] == "refines"]
    assert len(refines) == 3
    for link in refines:
        assert arts[link["source_id"]]["type"] == "user_story"
        assert arts[link["target_id"]]["type"] == "requirement"


def test_formalize_is_deterministic(client: TestClient) -> None:
    data = _formalize(client, "Users can create tasks")
    requirement = next(a for a in data["artifacts"] if a["type"] == "requirement")
    assert requirement["title"] == "Users can create tasks"
    assert requirement["source_ref"] == "project_description"

    story = next(a for a in data["artifacts"] if a["type"] == "user_story")
    assert story["title"].startswith("As a user, I want users can create tasks")
