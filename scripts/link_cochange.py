"""Research tooling: build co-change item links from git history.

Tests the hypothesis that "these files change together" predicts impact better than "this file
imports that one". Edges are mined from commits reachable from the pinned revision only — a
commit made after the analysed snapshot is knowledge the analysis could not have had.

This talks to the database directly on purpose: rebuilding an edge set per evaluation fold is
experiment scaffolding, not a product operation, and Engram's API deliberately has no way to
delete reviewed knowledge.

    python scripts/link_cochange.py --project <uuid> --pinned 18e3162 --exclude d92dc06
"""

from __future__ import annotations

import argparse
import itertools
import subprocess
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api" / "src"))

from sqlalchemy import delete, select, update  # noqa: E402

from engram.db.base import SessionLocal  # noqa: E402
from engram.enums import LinkOrigin, LinkState, LinkType  # noqa: E402
from engram.models import ArtifactItemRecord, EvidenceRef, ItemLink  # noqa: E402

MARKER = "Co-change:"
IMPORT_MARKER = "Static Python import edge"
SUFFIXES = {
    ".md", ".mdx", ".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".toml", ".yaml", ".yml", ".json",
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def mine_pairs(pinned: str, max_files: int, exclude: set[str]) -> Counter:
    """Count how often each pair of importable files changed in the same commit."""
    tree = {path for path in _git("ls-tree", "-r", "--name-only", pinned).splitlines() if path}
    pairs: Counter = Counter()
    for sha in _git("log", "--no-merges", "--format=%h", pinned).split():
        if sha in exclude:
            continue
        touched = sorted(
            {
                path
                for path in _git("show", "--pretty=format:", "--name-only", sha).splitlines()
                if path in tree and Path(path).suffix.lower() in SUFFIXES
            }
        )
        if not 2 <= len(touched) <= max_files:
            continue
        for left, right in itertools.combinations(touched, 2):
            pairs[(left, right)] += 1
    return pairs


def _representatives(session, project_id: uuid.UUID) -> dict[str, ArtifactItemRecord]:
    """One item per repository path: co-change is a path-level relation."""
    by_path: dict[str, ArtifactItemRecord] = {}
    items = session.scalars(
        select(ArtifactItemRecord).where(
            ArtifactItemRecord.project_id == project_id,
            ArtifactItemRecord.valid_to.is_(None),
        )
    ).all()
    for item in sorted(items, key=lambda value: value.key):
        path = item.title.split(" · ", 1)[0]
        by_path.setdefault(path, item)
    return by_path


def clear_links(session, project_id: uuid.UUID) -> int:
    stale = session.scalars(
        select(ItemLink.id).where(
            ItemLink.project_id == project_id, ItemLink.rationale.startswith(MARKER)
        )
    ).all()
    if stale:
        session.execute(
            delete(EvidenceRef).where(
                EvidenceRef.subject_type == "item_link", EvidenceRef.subject_id.in_(stale)
            )
        )
        session.execute(delete(ItemLink).where(ItemLink.id.in_(stale)))
    return len(stale)


def set_import_links(session, project_id: uuid.UUID, *, active: bool) -> int:
    """Park or restore the Python-import edges, so the two edge types can be compared alone."""
    state = LinkState.confirmed.value if active else LinkState.proposed.value
    result = session.execute(
        update(ItemLink)
        .where(
            ItemLink.project_id == project_id,
            ItemLink.rationale.startswith(IMPORT_MARKER),
        )
        .values(state=state)
    )
    return int(result.rowcount or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--pinned", default="18e3162", help="Mine only history up to this revision")
    parser.add_argument("--exclude", default="", help="Comma-separated commits to leave out")
    parser.add_argument("--max-files", type=int, default=15)
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--clear-only", action="store_true")
    parser.add_argument(
        "--import-links",
        choices=("keep", "park", "restore"),
        default="park",
        help="park = compare co-change edges on their own",
    )
    args = parser.parse_args()

    project_id = uuid.UUID(args.project)
    exclude = {value.strip() for value in args.exclude.split(",") if value.strip()}
    session = SessionLocal()
    try:
        removed = clear_links(session, project_id)
        if args.import_links == "park":
            parked = set_import_links(session, project_id, active=False)
        elif args.import_links == "restore":
            parked = set_import_links(session, project_id, active=True)
        else:
            parked = 0

        if args.clear_only:
            session.commit()
            print(f"cleared {removed} co-change links; import links touched: {parked}")
            return 0

        pairs = mine_pairs(args.pinned, args.max_files, exclude)
        representatives = _representatives(session, project_id)
        created = 0
        skipped = 0
        by_path_count: dict[str, int] = defaultdict(int)
        for (left, right), count in pairs.items():
            if count < args.min_count:
                continue
            source = representatives.get(left)
            target = representatives.get(right)
            if source is None or target is None or source.id == target.id:
                skipped += 1
                continue
            locator = source.source_locator_id or target.source_locator_id
            if locator is None:
                skipped += 1
                continue
            session.add(
                ItemLink(
                    project_id=project_id,
                    source_item_id=source.id,
                    target_item_id=target.id,
                    type=LinkType.related_to,
                    origin=LinkOrigin.imported.value,
                    confidence=min(1.0, 0.5 + 0.25 * count),
                    rationale=f"{MARKER} {left} and {right} changed together in {count} commit(s).",
                    evidence_locator_ids=[str(locator)],
                    state=LinkState.confirmed.value,
                    confirmed_by="cochange-linker",
                )
            )
            created += 1
            by_path_count[left] += 1
            by_path_count[right] += 1
        session.commit()
        hubs = sorted(by_path_count.items(), key=lambda kv: -kv[1])[:5]
        print(
            f"cleared {removed}, import links parked/restored {parked}, "
            f"created {created} co-change links (skipped {skipped}); "
            f"excluded={sorted(exclude) or '-'}"
        )
        print("  busiest paths: " + ", ".join(f"{path}({n})" for path, n in hubs))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
