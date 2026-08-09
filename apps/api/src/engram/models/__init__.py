"""ORM models package.

Every model is imported here so that ``Base.metadata`` is fully populated for Alembic
autogenerate and ``create_all`` (used by tests).
"""

from engram.models.analysis import (
    ChangeSet,
    ChangeSetItem,
    ContextPackage,
    ContextPackageItem,
    ImpactAnalysis,
    ImpactCandidate,
)
from engram.models.artifact import Artifact, ArtifactVersion
from engram.models.changelog import ChangeLog
from engram.models.item import ArtifactItemRecord, ItemLink, ItemVersion
from engram.models.link import ArtifactLink
from engram.models.project import DEFAULT_PROJECT_ID, Project
from engram.models.source import EvidenceRef, Source, SourceLocator, SourceRevision

__all__ = [
    "Artifact",
    "ArtifactVersion",
    "ArtifactLink",
    "ArtifactItemRecord",
    "ChangeLog",
    "ChangeSet",
    "ChangeSetItem",
    "ContextPackage",
    "ContextPackageItem",
    "DEFAULT_PROJECT_ID",
    "EvidenceRef",
    "ImpactAnalysis",
    "ImpactCandidate",
    "ItemLink",
    "ItemVersion",
    "Project",
    "Source",
    "SourceLocator",
    "SourceRevision",
]
