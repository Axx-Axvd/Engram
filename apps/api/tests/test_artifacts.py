from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _create(client: TestClient, **overrides: object) -> dict:
    payload = {"type": "requirement", "title": "Req A", "content": "body"}
    payload.update(overrides)
    resp = client.post("/api/artifacts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_and_get_artifact(client: TestClient) -> None:
    art = _create(client)
    assert art["type"] == "requirement"
    assert art["status"] == "draft"
    assert art["current_version"] == 1

    got = client.get(f"/api/artifacts/{art['id']}")
    assert got.status_code == 200
    assert got.json()["title"] == "Req A"

    versions = client.get(f"/api/artifacts/{art['id']}/versions").json()
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["is_active"] is True


def test_list_and_filter(client: TestClient) -> None:
    _create(client, type="requirement", title="R1")
    _create(client, type="user_story", title="S1")

    assert len(client.get("/api/artifacts").json()) == 2

    reqs = client.get("/api/artifacts", params={"type": "requirement"}).json()
    assert len(reqs) == 1
    assert reqs[0]["type"] == "requirement"


def test_update_creates_new_version(client: TestClient) -> None:
    art = _create(client)
    resp = client.patch(
        f"/api/artifacts/{art['id']}", json={"content": "updated", "reason": "refine"}
    )
    assert resp.status_code == 200
    assert resp.json()["current_version"] == 2
    assert resp.json()["content"] == "updated"

    versions = client.get(f"/api/artifacts/{art['id']}/versions").json()
    assert len(versions) == 2
    active = [v for v in versions if v["is_active"]]
    assert len(active) == 1
    assert active[0]["version"] == 2
    assert active[0]["reason"] == "refine"


def test_noop_update_keeps_version(client: TestClient) -> None:
    art = _create(client)
    resp = client.patch(f"/api/artifacts/{art['id']}", json={"title": "Req A"})
    assert resp.status_code == 200
    assert resp.json()["current_version"] == 1
    assert len(client.get(f"/api/artifacts/{art['id']}/versions").json()) == 1


def test_status_change_bumps_version(client: TestClient) -> None:
    art = _create(client)
    resp = client.patch(f"/api/artifacts/{art['id']}", json={"status": "approved"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["current_version"] == 2


def test_get_missing_returns_404(client: TestClient) -> None:
    resp = client.get(f"/api/artifacts/{uuid.uuid4()}")
    assert resp.status_code == 404
