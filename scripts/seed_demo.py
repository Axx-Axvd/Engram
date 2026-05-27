"""Seed the Engram dev database with a demo project (a small todo manager).

Run from the backend app so the `engram` package and the repo-root `.env` resolve:

    cd apps/api
    uv run python ../../scripts/seed_demo.py            # reset, then formalize
    uv run python ../../scripts/seed_demo.py --change   # also run a sample change request
    uv run python ../../scripts/seed_demo.py --no-reset  # append instead of clearing
"""

from __future__ import annotations

import argparse

from sqlalchemy import text

from engram.db.base import SessionLocal, engine
from engram.orchestration import get_workflow_engine
from engram.schemas.workflow import ChangeRequestInput, FormalizeRequest

DESCRIPTION = """\
TaskFlow is a simple todo manager.
Users can create tasks with a title, description, and due date.
Users can mark tasks as complete or reopen them.
Users can organize tasks into named lists.
Users can share a list with teammates and assign tasks to people.
Users can filter and search tasks by status, due date, and assignee.
"""

CHANGE = "Add recurring tasks that repeat on a daily, weekly, or monthly schedule."

_TABLES = "artifacts, artifact_versions, artifact_links, change_logs"


def reset() -> None:
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Engram dev DB with a demo project.")
    parser.add_argument(
        "--no-reset", action="store_true", help="append instead of clearing existing data first"
    )
    parser.add_argument(
        "--change", action="store_true", help="also run a sample change request"
    )
    args = parser.parse_args()

    if not args.no_reset:
        reset()
        print("- reset: cleared existing artifacts")

    engine_wf = get_workflow_engine()
    with SessionLocal() as session:
        result = engine_wf.formalize(
            session, FormalizeRequest(description=DESCRIPTION, created_by="seed")
        )
        session.commit()
        print(f"- formalized: {len(result.artifacts)} documents, {len(result.links)} links")
        for artifact in result.artifacts:
            count = len(artifact.items)
            suffix = f" ({count} items)" if count else ""
            print(f"    [{artifact.type}] {artifact.title}{suffix}")

        if args.change:
            impact = engine_wf.analyze_change(
                session, ChangeRequestInput(text=CHANGE, created_by="seed")
            )
            session.commit()
            print(f"- change request: impacted {len(impact.impacted)} documents")

    print("\nDone. Start the API and web app, then open http://localhost:3000")


if __name__ == "__main__":
    main()
