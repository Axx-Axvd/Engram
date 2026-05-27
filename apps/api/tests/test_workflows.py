from __future__ import annotations

from fastapi.testclient import TestClient


def _formalize(client: TestClient, description: str) -> dict:
    resp = client.post("/api/workflows/formalize", json={"description": description})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_formalize_produces_five_grouped_documents(client: TestClient) -> None:
    desc = "Users can create tasks. Users can complete tasks. Users group tasks into lists."
    data = _formalize(client, desc)
    arts = data["artifacts"]

    by_type = {a["type"]: a for a in arts}
    assert len(arts) == 5
    assert set(by_type) == {
        "project_brief",
        "requirement",
        "user_story",
        "task",
        "test_case",
    }

    # Three sentences -> three items in each type document.
    requirements = by_type["requirement"]
    assert len(requirements["items"]) == 3
    assert all(item["key"].startswith("R") for item in requirements["items"])
    assert all(item["feature"] for item in requirements["items"])

    # Other documents carry the same number of items, each referencing a requirement key.
    for doc_type in ("user_story", "task", "test_case"):
        assert len(by_type[doc_type]["items"]) == 3


def test_formalize_items_reference_requirement_keys(client: TestClient) -> None:
    data = _formalize(client, "Users can create tasks. Users can share lists with teammates.")
    by_type = {a["type"]: a for a in data["artifacts"]}
    requirements = by_type["requirement"]
    req_keys = {item["key"] for item in requirements["items"]}

    for task in by_type["task"]["items"]:
        assert task["refs"], "task item should reference a requirement"
        ref = task["refs"][0]
        assert ref["artifact_id"] == requirements["id"]
        assert ref["key"] in req_keys


def test_formalize_links_documents_to_brief_and_requirements(client: TestClient) -> None:
    data = _formalize(client, "Users can create tasks. Users can share lists.")
    link_types = [link["type"] for link in data["links"]]
    assert link_types.count("derived_from") == 4  # each doc derives from the brief
    assert "refines" in link_types  # stories -> requirements
    assert "implements" in link_types  # tasks -> requirements
    assert "tests" in link_types  # tests -> requirements


def test_formalize_is_deterministic(client: TestClient) -> None:
    data = _formalize(client, "Users can create tasks")
    requirements = next(a for a in data["artifacts"] if a["type"] == "requirement")
    assert requirements["items"][0]["title"] == "Users can create tasks"

    brief = next(a for a in data["artifacts"] if a["type"] == "project_brief")
    assert brief["content"] == "Users can create tasks"
