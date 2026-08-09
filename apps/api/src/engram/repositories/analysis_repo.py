"""Impact-analysis and package persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from engram.models import ChangeSet, ContextPackage, ImpactAnalysis, ImpactCandidate


def get_analysis(
    session: Session, project_id: uuid.UUID, analysis_id: uuid.UUID
) -> ImpactAnalysis | None:
    return session.scalars(
        select(ImpactAnalysis).where(
            ImpactAnalysis.id == analysis_id,
            ImpactAnalysis.project_id == project_id,
        )
    ).first()


def list_analyses(session: Session, project_id: uuid.UUID) -> list[ImpactAnalysis]:
    return list(
        session.scalars(
            select(ImpactAnalysis)
            .where(ImpactAnalysis.project_id == project_id)
            .order_by(ImpactAnalysis.created_at.desc())
        )
    )


def list_candidates(session: Session, analysis_id: uuid.UUID) -> list[ImpactCandidate]:
    return list(
        session.scalars(select(ImpactCandidate).where(ImpactCandidate.analysis_id == analysis_id))
    )


def get_candidate(
    session: Session, analysis_id: uuid.UUID, candidate_id: uuid.UUID
) -> ImpactCandidate | None:
    return session.scalars(
        select(ImpactCandidate).where(
            ImpactCandidate.id == candidate_id,
            ImpactCandidate.analysis_id == analysis_id,
        )
    ).first()


def get_package(
    session: Session, project_id: uuid.UUID, package_id: uuid.UUID
) -> ContextPackage | None:
    return session.scalars(
        select(ContextPackage).where(
            ContextPackage.id == package_id,
            ContextPackage.project_id == project_id,
        )
    ).first()


def list_packages(session: Session, project_id: uuid.UUID) -> list[ContextPackage]:
    return list(
        session.scalars(
            select(ContextPackage)
            .where(ContextPackage.project_id == project_id)
            .order_by(ContextPackage.created_at.desc())
        )
    )


def get_change_set(
    session: Session, project_id: uuid.UUID, change_set_id: uuid.UUID
) -> ChangeSet | None:
    return session.scalars(
        select(ChangeSet).where(
            ChangeSet.id == change_set_id,
            ChangeSet.project_id == project_id,
        )
    ).first()


def list_change_sets(session: Session, project_id: uuid.UUID) -> list[ChangeSet]:
    return list(
        session.scalars(
            select(ChangeSet)
            .where(ChangeSet.project_id == project_id)
            .order_by(ChangeSet.created_at.desc())
        )
    )


def add(session: Session, value):
    session.add(value)
    session.flush()
    return value
