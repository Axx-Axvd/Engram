"""Deterministic import-graph linker for a dogfooded Engram project.

Parses Python import edges from imported code items and creates file-level typed
item links: test items -> `tests` -> code_component, code_component -> `depends_on`
-> code_component. Resolution uses both a module map and a top-level symbol map so
that `from engram.models import Artifact` links to models/artifact.py, not the package.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter

BASE = "http://localhost:8000"
PID = sys.argv[1]
REV = sys.argv[2] if len(sys.argv) > 2 else None
SEP = " · "  # the " · " separator used in imported item titles


def req(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


def path_of(it: dict) -> str:
    return it["title"].split(SEP, 1)[0]


def module_of(path: str) -> str | None:
    if path.startswith("apps/api/src/") and path.endswith(".py"):
        rel = path[len("apps/api/src/"):-3]
        if rel.endswith("/__init__"):
            rel = rel[: -len("/__init__")]
        return rel.replace("/", ".")
    return None


st, items = req("GET", f"/api/projects/{PID}/items")
if st != 200:
    print("FAILED to list items:", st, items)
    raise SystemExit(1)

code_items: list[tuple[dict, str]] = []
module_map: dict[str, dict] = {}
symbol_map: dict[str, dict] = {}
for it in items:
    p = path_of(it)
    if not p.endswith(".py"):
        continue
    code_items.append((it, p))
    mod = module_of(p)
    if mod:
        module_map.setdefault(mod, it)
    if p.startswith("apps/api/src/"):
        for mo in re.finditer(r"^(?:class|def)\s+([A-Za-z_]\w*)", it["text"], re.M):
            symbol_map.setdefault(mo.group(1), it)

print(f"code items: {len(code_items)}  modules: {len(module_map)}  symbols: {len(symbol_map)}")


def resolve(base: str, name: str) -> dict | None:
    cand = f"{base}.{name}"
    if cand in module_map:
        return module_map[cand]
    if name in symbol_map:
        return symbol_map[name]
    return module_map.get(base)


def targets_for(text: str) -> set[str]:
    out: set[str] = set()
    for mo in re.finditer(r"^\s*from\s+(engram[\w.]*)\s+import\s+(.+)$", text, re.M):
        base = mo.group(1)
        rest = mo.group(2).split("#", 1)[0]
        for name in re.findall(r"[A-Za-z_]\w*", rest):
            if name == "import":
                continue
            tgt = resolve(base, name)
            if tgt:
                out.add(tgt["id"])
    for mo in re.finditer(r"^\s*import\s+(engram[\w.]*)", text, re.M):
        base = mo.group(1)
        if base in module_map:
            out.add(module_map[base]["id"])
    return out


created = Counter()
dup = 0
rejected = 0
for it, p in code_items:
    ltype = "tests" if it["type"] == "test" else "depends_on"
    for tgt_id in targets_for(it["text"]):
        if tgt_id == it["id"]:
            continue
        body = {
            "source_item_id": it["id"],
            "target_item_id": tgt_id,
            "type": ltype,
            "origin": "imported",
            "state": "confirmed",
            "confidence": 1.0,
            "rationale": f"Static Python import edge ({ltype}) parsed from {p}.",
            "created_by": "linker",
        }
        if REV:
            body["source_revision_id"] = REV
        st, resp = req("POST", f"/api/projects/{PID}/item-links", body)
        if st == 201:
            created[ltype] += 1
        elif st == 409:
            dup += 1
        else:
            rejected += 1

print("created:", dict(created), "dup:", dup, "rejected:", rejected)
st, links = req("GET", f"/api/projects/{PID}/item-links")
if st == 200:
    by = Counter((l["type"], l["state"]) for l in links)
    print("total item-links:", len(links))
    for k, v in sorted(by.items()):
        print(f"  {k}: {v}")
