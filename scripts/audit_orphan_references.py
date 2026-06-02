"""Audit a user productivity database for orphan references and consistency issues.

Background
----------
The productivity tools historically did not validate foreign-key references
(like ``project_id`` on a journal) at the time of insertion, so orphan rows
could be created if a tool call referenced a non-existent project or task.
The current tool/service layer now rejects such calls (B1-B4), but rows
that were created before that fix may still be present in user databases.

This script scans a user SQLite database and reports:

- ``journalentry`` rows whose ``project_id`` is set but the project does
  not exist.
- ``projecttasklink`` rows whose ``project_id`` or ``task_id`` does not
  exist in its parent table.
- ``task`` rows whose ``completed_at`` is non-null but ``status`` is not
  ``'completed'`` (consistency check, free with the same scan).

The script is report-only. It never modifies the database. If a fix mode
is needed in the future, that should be a separate, opt-in tool that
backs up the database first.

Usage
-----
    uv run python scripts/audit_orphan_references.py sqlite:///path/to/user.db
"""

import argparse
import sys

from genesis_core.productivity.models import Status
from sqlalchemy import text
from sqlmodel import create_engine

# Status values that mean "done". Anything else with a non-null
# completed_at is suspicious.
DONE_STATUSES: set[str] = {Status.COMPLETED.value, Status.CANCELED.value}


def _connect_args(db_url: str) -> dict:
    return {"check_same_thread": False} if db_url.startswith("sqlite") else {}


def audit(db_url: str) -> int:
    """Run all audit checks against the given database URL.

    Returns the total number of issues found.
    """
    engine = create_engine(db_url, echo=False, connect_args=_connect_args(db_url))

    issues = 0

    with engine.connect() as conn:
        # 1. Journal entries whose project_id is set but the project is gone.
        #    Use raw SQL to avoid the SQLAlchemy enum processor failing on
        #    corrupt status values.
        orphan_journals = list(
            conn.execute(
                text(
                    """
                    SELECT id, entry_type, title, project_id
                    FROM journalentry
                    WHERE project_id IS NOT NULL
                      AND project_id NOT IN (SELECT id FROM project)
                    """,
                ),
            ).all(),
        )
        for row in orphan_journals:
            issues += 1
            print(
                f"  [Orphan journal]    id={row[0]} type={row[1]!r} title={row[2]!r} project_id={row[3]}",
                file=sys.stderr,
            )

        # 2. ProjectTaskLink rows pointing at a missing project or task.
        orphan_links = list(
            conn.execute(
                text(
                    """
                    SELECT project_id, task_id
                    FROM projecttasklink
                    WHERE project_id NOT IN (SELECT id FROM project)
                       OR task_id NOT IN (SELECT id FROM task)
                    """,
                ),
            ).all(),
        )
        for row in orphan_links:
            issues += 1
            print(
                f"  [Orphan link]       project_id={row[0]} task_id={row[1]}",
                file=sys.stderr,
            )

        # 3. Tasks with completed_at but status is not "done". This is a
        #    consistency check: the service auto-sets completed_at when
        #    status flips to 'completed', and clears it when reopened, so
        #    the two should agree. Any mismatch points to a hand-edited DB
        #    or a row written before that auto-handling was in place.
        inconsistent_tasks = list(
            conn.execute(
                text(
                    """
                    SELECT id, title, status, completed_at
                    FROM task
                    WHERE completed_at IS NOT NULL
                    """,
                ),
            ).all(),
        )
        for row in inconsistent_tasks:
            status_value = row[2]
            if status_value not in DONE_STATUSES:
                issues += 1
                print(
                    f"  [Inconsistent task] id={row[0]} title={row[1]!r} status={status_value!r} completed_at={row[3]!r}",
                    file=sys.stderr,
                )

    if issues == 0:
        print("No orphan references or consistency issues found.", file=sys.stderr)
    else:
        print(f"\nFound {issues} issue(s).", file=sys.stderr)
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit a user productivity database for orphan references and consistency issues.",
    )
    parser.add_argument(
        "db_url",
        help="SQLAlchemy database URL, e.g. sqlite:///path/to/user.db",
    )
    args = parser.parse_args()

    print(f"Auditing {args.db_url}...", file=sys.stderr)
    audit(args.db_url)


if __name__ == "__main__":
    main()
