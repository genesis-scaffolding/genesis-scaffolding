"""Repair user productivity databases that have invalid status values.

Background
----------
The agent tool ``update_tasks`` historically did not validate the ``status``
argument against the ``Status`` enum. An agent could therefore write any
string (for example ``"deleted"``) to a task. The corrupt value persisted
because the service layer used ``setattr`` to bypass Pydantic validation, and
any later page that loaded the task list crashed because SQLAlchemy's enum
processor could not coerce the value back on read.

This script uses raw SQL (bypassing the SQLModel enum validation) to find
rows whose ``status`` is not in the current ``Status`` enum and either
reports them (default, dry-run) or sets them to ``Status.CANCELED`` (the
safest non-destructive fallback for an ambiguous invalid value).

Usage
-----
Scan only (dry-run, the default):

    uv run python scripts/repair_invalid_status.py sqlite:///path/to/user.db

Apply the fix (prompts for confirmation):

    uv run python scripts/repair_invalid_status.py sqlite:///path/to/user.db --apply
"""

import argparse
import sys

from genesis_core.productivity.models import Status
from sqlalchemy import text
from sqlmodel import create_engine

VALID_STATUSES: set[str] = {s.value for s in Status}
# SQLAlchemy's Enum type stores the member *name* (uppercase) by default,
# not the lowercase value, so the column is checked against names on read.
# We accept both the lowercase value and the uppercase name as "valid"
# when scanning, so we do not flag rows that are already correct.
VALID_STATUS_NAMES: set[str] = {s.name for s in Status}
VALID_DB_VALUES: set[str] = VALID_STATUSES | VALID_STATUS_NAMES
# The format SQLAlchemy actually stores when given a Status member.
CANCELED_DB_VALUE: str = Status.CANCELED.name


def _connect_args(db_url: str) -> dict:
    return {"check_same_thread": False} if db_url.startswith("sqlite") else {}


def scan_or_repair(db_url: str, apply_fix: bool) -> int:
    """Scan the database for invalid status values and optionally repair.

    Returns the number of rows that were (or would be, in dry-run) repaired.
    """
    engine = create_engine(db_url, echo=False, connect_args=_connect_args(db_url))

    with engine.begin() as conn:
        # Read raw values to bypass the SQLAlchemy enum processor, which
        # would otherwise raise LookupError on a corrupt row.
        task_rows = list(
            conn.execute(
                text("SELECT id, title, status FROM task"),
            ).all(),
        )
        project_rows = list(
            conn.execute(
                text("SELECT id, name, status FROM project"),
            ).all(),
        )

    invalid_task_ids: list[int] = []
    invalid_project_ids: list[int] = []

    for row in task_rows:
        current = row[2]
        if current not in VALID_DB_VALUES:
            invalid_task_ids.append(row[0])
            print(
                f"  [Task]     id={row[0]} title={row[1]!r} status={current!r}",
                file=sys.stderr,
            )

    for row in project_rows:
        current = row[2]
        if current not in VALID_DB_VALUES:
            invalid_project_ids.append(row[0])
            print(
                f"  [Project]  id={row[0]} name={row[1]!r} status={current!r}",
                file=sys.stderr,
            )

    if not invalid_task_ids and not invalid_project_ids:
        print("No invalid status values found.", file=sys.stderr)
        return 0

    if apply_fix:
        with engine.begin() as conn:
            for task_id in invalid_task_ids:
                conn.execute(
                    text("UPDATE task SET status = :status WHERE id = :id"),
                    {"status": CANCELED_DB_VALUE, "id": task_id},
                )
            for project_id in invalid_project_ids:
                conn.execute(
                    text("UPDATE project SET status = :status WHERE id = :id"),
                    {"status": CANCELED_DB_VALUE, "id": project_id},
                )
        total = len(invalid_task_ids) + len(invalid_project_ids)
        print(
            f"Repaired {total} rows "
            f"({len(invalid_task_ids)} tasks, {len(invalid_project_ids)} projects) "
            f"to status='{CANCELED_DB_VALUE}'.",
            file=sys.stderr,
        )
        return total

    total = len(invalid_task_ids) + len(invalid_project_ids)
    print(
        f"\nFound {total} rows with invalid status "
        f"({len(invalid_task_ids)} tasks, {len(invalid_project_ids)} projects). "
        f"Re-run with --apply to set them to '{CANCELED_DB_VALUE}'.",
        file=sys.stderr,
    )
    return total


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan or repair invalid status values in a user productivity database.",
    )
    parser.add_argument(
        "db_url",
        help="SQLAlchemy database URL, e.g. sqlite:///path/to/user.db",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually modify the database. Default is dry-run (report only).",
    )
    args = parser.parse_args()

    if args.apply:
        print(
            f"WARNING: This will modify '{args.db_url}'.\nMake sure you have a backup before continuing.",
            file=sys.stderr,
        )
        response = input("Type 'yes' to continue: ")
        if response.strip().lower() != "yes":
            print("Aborted.", file=sys.stderr)
            sys.exit(1)

    print(f"Scanning {args.db_url} (apply={args.apply})...", file=sys.stderr)
    scan_or_repair(args.db_url, args.apply)


if __name__ == "__main__":
    main()
