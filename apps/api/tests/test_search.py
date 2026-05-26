from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from engram.models import Artifact


def _create(client: TestClient, **overrides: object) -> dict:
    payload = {"type": "requirement", "title": "Untitled", "content": ""}
    payload.update(overrides)
    resp = client.post("/api/artifacts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _context(client: TestClient, query: str, **opts: object) -> dict:
    resp = client.post("/api/search/context", json={"query": query, **opts})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_embedding_stored_on_create(client: TestClient, db_session: Session) -> None:
    art = _create(client, title="Shopping cart checkout")
    stored = db_session.get(Artifact, uuid.UUID(art["id"]))
    assert stored is not None
    assert stored.embedding is not None
    assert len(stored.embedding) == 384


def test_vector_retrieval_ranks_lexical_match_first(client: TestClient) -> None:
    target = _create(client, title="Shopping cart checkout")
    _create(client, title="User profile settings")
    _create(client, title="Email notifications")

    bundle = _context(client, "checkout", limit=5, hops=0)
    assert bundle["seed_ids"][0] == target["id"]


def test_graph_expansion_pulls_in_linked_neighbor(client: TestClient) -> None:
    req = _create(client, type="requirement", title="Checkout flow")
    story = _create(client, type="user_story", title="Guest mode")  # no "checkout" token
    assert (
        client.post(
            "/api/links",
            json={"source_id": story["id"], "target_id": req["id"], "type": "refines"},
        ).status_code
        == 201
    )

    bundle = _context(client, "checkout", limit=5, hops=1)
    assert req["id"] in bundle["seed_ids"]
    artifact_ids = {a["id"] for a in bundle["artifacts"]}
    assert story["id"] in artifact_ids  # pulled in via the link
    assert any(link["type"] == "refines" for link in bundle["links"])


def test_archived_excluded_from_context(client: TestClient) -> None:
    art = _create(client, title="Payment gateway integration")
    resp = client.patch(f"/api/artifacts/{art['id']}", json={"status": "archived"})
    assert resp.status_code == 200

    bundle = _context(client, "payment")
    assert art["id"] not in bundle["seed_ids"]
    assert art["id"] not in {a["id"] for a in bundle["artifacts"]}
