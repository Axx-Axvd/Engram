"""Read-only GitHub ingestion at an immutable commit SHA."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from engram.config import settings
from engram.enums import ItemType, LinkOrigin, LinkState, LinkType, SourceKind
from engram.errors import NotFoundError, ValidationError
from engram.models import (
    ArtifactItemRecord,
    ChangeSet,
    ChangeSetItem,
    Source,
    SourceLocator,
    SourceRevision,
)
from engram.repositories import analysis_repo, item_repo, source_repo
from engram.schemas.item import ItemLinkCreate
from engram.schemas.source import (
    GitHubSourceCreate,
    SourceCreate,
    SourceSyncResult,
)
from engram.services import item_service, project_service, provenance_service

_IMPORT_SUFFIXES = {
    ".md",
    ".mdx",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".sql",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
}
_MAX_FILES = 500
_MAX_FILE_BYTES = 250_000
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class GitHubClient:
    def __init__(self) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        self._client = httpx.Client(
            base_url=settings.github_api_url.rstrip("/"),
            headers=headers,
            timeout=30,
            follow_redirects=True,
        )

    def json(self, path: str, *, params: dict | None = None):
        response = self._client.get(path, params=params)
        if response.status_code == 404:
            raise NotFoundError(f"GitHub resource not found: {path}")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValidationError(f"GitHub returned {response.status_code} for {path}") from exc
        return response.json()

    def text(self, path: str, *, params: dict | None = None) -> str:
        response = self._client.get(
            path,
            params=params,
            headers={"Accept": "application/vnd.github.raw+json"},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValidationError(f"GitHub returned {response.status_code} for {path}") from exc
        if len(response.content) > _MAX_FILE_BYTES:
            raise ValidationError(f"GitHub source file is too large: {path}")
        return response.text


@dataclass(frozen=True)
class _Chunk:
    title: str
    text: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class _Imported:
    item_id: uuid.UUID
    before_version_id: uuid.UUID | None
    after_version_id: uuid.UUID
    created: bool
    content_changed: bool
    change_kind: str


def create_github_source(
    session: Session, project_id: uuid.UUID, data: GitHubSourceCreate
) -> Source:
    return provenance_service.create_source(
        session,
        project_id,
        SourceCreate(
            kind=SourceKind.github,
            name=data.repository,
            url=f"https://github.com/{data.repository}",
            configuration={"repository": data.repository, "ref": data.ref},
            created_by=data.created_by,
        ),
    )


def _chunks(path: str, content: str) -> list[_Chunk]:
    lines = content.splitlines()
    if PurePosixPath(path).suffix.lower() not in {".md", ".mdx"}:
        return [
            _Chunk(
                title=PurePosixPath(path).name,
                text=content,
                start_line=1,
                end_line=max(1, len(lines)),
            )
        ]
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines, start=1):
        match = _HEADING.match(line)
        if match:
            headings.append((index, match.group(2).strip()))
    if not headings:
        return [
            _Chunk(
                title=PurePosixPath(path).name,
                text=content,
                start_line=1,
                end_line=max(1, len(lines)),
            )
        ]
    result: list[_Chunk] = []
    for position, (start, title) in enumerate(headings):
        end = headings[position + 1][0] - 1 if position + 1 < len(headings) else len(lines)
        result.append(
            _Chunk(
                title=title,
                text="\n".join(lines[start - 1 : end]).strip(),
                start_line=start,
                end_line=max(start, end),
            )
        )
    return result


def _stable_key(repository: str, identity: str) -> str:
    return "GH-" + hashlib.sha256(f"{repository}:{identity}".encode()).hexdigest()[:20].upper()


def _file_type(path: str) -> ItemType:
    lowered = path.lower()
    name = PurePosixPath(path).name.lower()
    if "/adr/" in f"/{lowered}" or name.startswith("adr-"):
        return ItemType.decision
    if any(token in lowered for token in ("test", "spec")) and PurePosixPath(path).suffix != ".md":
        return ItemType.test
    if PurePosixPath(path).suffix.lower() in {".md", ".mdx"}:
        if any(token in lowered for token in ("requirement", "specification", "requirements")):
            return ItemType.requirement
        return ItemType.document
    return ItemType.code_component


def _upsert(
    session: Session,
    *,
    project_id: uuid.UUID,
    key: str,
    type_: ItemType,
    title: str,
    text: str,
    locator_id: uuid.UUID,
    created_by: str,
) -> _Imported:
    previous = next(
        (
            item
            for item in item_repo.list_items(session, project_id, include_stale=True)
            if item.artifact_id is None and item.key == key and item.type == type_.value
        ),
        None,
    )
    before_id = previous.current_version_id if previous is not None else None
    content_changed = previous is None or previous.title != title or previous.text != text
    item, created_or_versioned = item_service.upsert_imported_item(
        session,
        project_id=project_id,
        artifact_id=None,
        key=key,
        type_=type_,
        title=title,
        text=text,
        source_locator_id=locator_id,
        created_by=created_by,
    )
    if item.current_version_id is None:
        raise ValidationError("Imported item has no active version")
    return _Imported(
        item_id=item.id,
        before_version_id=before_id,
        after_version_id=item.current_version_id,
        created=previous is None,
        content_changed=content_changed and created_or_versioned,
        change_kind="added" if previous is None else "modified",
    )


def _current_source_items(
    session: Session, project_id: uuid.UUID, source_id: uuid.UUID
) -> list[ArtifactItemRecord]:
    return list(
        session.scalars(
            select(ArtifactItemRecord)
            .join(SourceLocator, ArtifactItemRecord.source_locator_id == SourceLocator.id)
            .join(SourceRevision, SourceLocator.source_revision_id == SourceRevision.id)
            .where(
                ArtifactItemRecord.project_id == project_id,
                ArtifactItemRecord.valid_to.is_(None),
                SourceRevision.source_id == source_id,
            )
        )
    )


def _import_file(
    session: Session,
    *,
    client: GitHubClient,
    project_id: uuid.UUID,
    revision: SourceRevision,
    repository: str,
    sha: str,
    path: str,
    created_by: str,
) -> list[_Imported]:
    content = client.text(
        f"/repos/{repository}/contents/{quote(path, safe='/')}", params={"ref": sha}
    )
    imported: list[_Imported] = []
    type_ = _file_type(path)
    for chunk in _chunks(path, content):
        locator = provenance_service.create_locator(
            session,
            revision,
            kind="file",
            path=path,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            url=f"https://github.com/{repository}/blob/{sha}/{quote(path, safe='/')}",
            content=chunk.text,
        )
        identity = f"{path}:{chunk.title}"
        imported.append(
            _upsert(
                session,
                project_id=project_id,
                key=_stable_key(repository, identity),
                type_=type_,
                title=f"{path} · {chunk.title}",
                text=chunk.text,
                locator_id=locator.id,
                created_by=created_by,
            )
        )
    return imported


def _import_external_record(
    session: Session,
    *,
    project_id: uuid.UUID,
    revision: SourceRevision,
    repository: str,
    kind: str,
    number_or_sha: str,
    title: str,
    text: str,
    url: str | None,
    type_: ItemType,
    created_by: str,
) -> _Imported:
    locator = provenance_service.create_locator(
        session,
        revision,
        kind=kind,
        external_id=number_or_sha,
        url=url,
        content=text,
    )
    return _upsert(
        session,
        project_id=project_id,
        key=_stable_key(repository, f"{kind}:{number_or_sha}"),
        type_=type_,
        title=title,
        text=text,
        locator_id=locator.id,
        created_by=created_by,
    )


def sync_github_source(
    session: Session,
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    *,
    ref: str | None,
    analysis_id: uuid.UUID | None,
    created_by: str,
    client: GitHubClient | None = None,
) -> SourceSyncResult:
    project_service.get_project(session, project_id)
    source = source_repo.get(session, source_id, project_id)
    if source is None:
        raise NotFoundError(f"Source {source_id} not found")
    if source.kind != SourceKind.github.value:
        raise ValidationError("Only GitHub sources can use the GitHub sync operation")
    if (
        analysis_id is not None
        and analysis_repo.get_analysis(session, project_id, analysis_id) is None
    ):
        raise ValidationError("Impact analysis does not belong to the selected project")
    repository = str(source.configuration.get("repository") or source.name)
    selected_ref = ref or str(source.configuration.get("ref") or "main")
    github = client or GitHubClient()
    commit = github.json(f"/repos/{repository}/commits/{quote(selected_ref, safe='')}")
    sha = str(commit["sha"])
    existing_revision = source_repo.find_revision(session, source.id, sha)
    if existing_revision is not None:
        return SourceSyncResult(
            source=source,
            revision=existing_revision,
            imported_items=0,
            updated_items=0,
            deleted_items=0,
            stale_links=0,
        )

    previous_items = _current_source_items(session, project_id, source.id)

    revision = provenance_service.create_revision(
        session,
        source,
        sha,
        revision_url=commit.get("html_url"),
        metadata={
            "ref": selected_ref,
            "message": commit.get("commit", {}).get("message"),
            "author_date": commit.get("commit", {}).get("author", {}).get("date"),
        },
    )
    tree = github.json(f"/repos/{repository}/git/trees/{sha}", params={"recursive": "1"})
    if tree.get("truncated"):
        raise ValidationError("GitHub tree is truncated; refusing an incomplete source revision")
    paths = [
        entry["path"]
        for entry in tree.get("tree", [])
        if entry.get("type") == "blob"
        and PurePosixPath(entry["path"]).suffix.lower() in _IMPORT_SUFFIXES
        and int(entry.get("size") or 0) <= _MAX_FILE_BYTES
    ]
    if len(paths) > _MAX_FILES:
        raise ValidationError(
            f"GitHub source contains {len(paths)} importable files; limit is {_MAX_FILES}"
        )

    imported: list[_Imported] = []
    for path in sorted(paths):
        imported.extend(
            _import_file(
                session,
                client=github,
                project_id=project_id,
                revision=revision,
                repository=repository,
                sha=sha,
                path=path,
                created_by=created_by,
            )
        )

    commit_import = _import_external_record(
        session,
        project_id=project_id,
        revision=revision,
        repository=repository,
        kind="commit",
        number_or_sha=sha,
        title=str(commit.get("commit", {}).get("message") or sha).splitlines()[0],
        text=str(commit.get("commit", {}).get("message") or ""),
        url=commit.get("html_url"),
        type_=ItemType.commit,
        created_by=created_by,
    )
    imported.append(commit_import)

    records = github.json(f"/repos/{repository}/issues", params={"state": "all", "per_page": 100})
    for record in records:
        is_pr = "pull_request" in record
        kind = "pull_request" if is_pr else "issue"
        imported.append(
            _import_external_record(
                session,
                project_id=project_id,
                revision=revision,
                repository=repository,
                kind=kind,
                number_or_sha=str(record["number"]),
                title=f"#{record['number']} {record.get('title') or ''}".strip(),
                text=str(record.get("body") or ""),
                url=record.get("html_url"),
                type_=ItemType.pull_request if is_pr else ItemType.issue,
                created_by=created_by,
            )
        )

    imported_ids = {value.item_id for value in imported}
    deleted_items = [item for item in previous_items if item.id not in imported_ids]
    for item in deleted_items:
        old_locator = source_repo.get_locator(session, item.source_locator_id)
        deletion_locator = provenance_service.create_locator(
            session,
            revision,
            kind="deleted",
            path=old_locator.path if old_locator is not None else None,
            external_id=old_locator.external_id if old_locator is not None else item.key,
            content="",
        )
        before_version_id = item.current_version_id
        version = item_service.mark_item_stale(
            session,
            item,
            source_locator_id=deletion_locator.id,
            reason="missing from imported source revision",
            created_by=created_by,
        )
        imported.append(
            _Imported(
                item_id=item.id,
                before_version_id=before_version_id,
                after_version_id=version.id,
                created=False,
                content_changed=True,
                change_kind="deleted",
            )
        )

    change_set = ChangeSet(
        project_id=project_id,
        analysis_id=analysis_id,
        source_revision_id=revision.id,
        external_id=sha,
        external_url=commit.get("html_url"),
        status="imported",
        summary=str(commit.get("commit", {}).get("message") or ""),
    )
    session.add(change_set)
    session.flush()
    changed_ids: set[uuid.UUID] = set()
    for value in imported:
        if not (value.created or value.content_changed):
            continue
        changed_ids.add(value.item_id)
        session.add(
            ChangeSetItem(
                change_set_id=change_set.id,
                item_id=value.item_id,
                before_version_id=value.before_version_id,
                after_version_id=value.after_version_id,
                change_kind=value.change_kind,
            )
        )
        if (
            value.item_id != commit_import.item_id
            and item_repo.find_link(session, commit_import.item_id, value.item_id, LinkType.changes)
            is None
        ):
            item_service.create_link(
                session,
                project_id,
                ItemLinkCreate(
                    source_item_id=commit_import.item_id,
                    target_item_id=value.item_id,
                    type=LinkType.changes,
                    origin=LinkOrigin.imported,
                    confidence=1.0,
                    rationale="The imported commit contains this changed source element.",
                    state=LinkState.confirmed,
                    source_revision_id=revision.id,
                    created_by=created_by,
                ),
            )
    stale_links = item_service.mark_links_stale(
        session, project_id, changed_ids - {commit_import.item_id}
    )
    # Imported causal links from this revision are current, even if a changed endpoint was marked.
    for link in item_repo.links_touching(session, project_id, {commit_import.item_id}):
        if link.source_revision_id == revision.id:
            link.state = LinkState.confirmed.value
    session.flush()
    return SourceSyncResult(
        source=source,
        revision=revision,
        imported_items=sum(1 for value in imported if value.created),
        updated_items=sum(
            1
            for value in imported
            if not value.created and value.content_changed and value.change_kind == "modified"
        ),
        deleted_items=sum(1 for value in imported if value.change_kind == "deleted"),
        stale_links=stale_links,
        change_set_id=change_set.id,
    )
