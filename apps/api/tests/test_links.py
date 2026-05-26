from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _create(client: TestClient, **overrides: object) -> dict:
    payload = {"type": "requirement", "title": "Req", "content": ""}
    payload.update(overrides)
    resp = client.post("/api/artifacts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_and_list_link(client: TestClient) -> None:
    a = _create(client, type="requirement", title="R")
    b = _create(client, type="user_story", title="S")

    resp = client.post(
        "/api/links", json={"source_id": a["id"], "target_id": b["id"], "type": "refines"}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["type"] == "refines"

    links = client.get(f"/api/artifacts/{a['id']}/links").json()
    assert len(links) == 1
    assert links[0]["target_id"] == b["id"]


def test_duplicate_link_conflict(client: TestClient) -> None:
    a = _create(client)
    b = _create(client)
    body = {"source_id": a["id"], "target_id": b["id"], "type": "related_to"}
    assert client.post("/api/links", json=body).status_code == 201
    assert client.post("/api/links", json=body).status_code == 409


def test_self_link_rejected(client: TestClient) -> None:
    a = _create(client)
    resp = client.post(
        "/api/links", json={"source_id": a["id"], "target_id": a["id"], "type": "related_to"}
    )
    assert resp.status_code == 422


def test_link_missing_target_404(client: TestClient) -> None:
    a = _create(client)
    resp = client.post(
        "/api/links",
        json={"source_id": a["id"], "target_id": str(uuid.uuid4()), "type": "refines"},
    )
    assert resp.status_code == 404
