import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from models import Contest

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "contests.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS contests (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    name TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    url TEXT NOT NULL,
    calendar_event_id TEXT,
    synced_at TEXT
)
"""

META_SCHEMA = "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"


@contextmanager
def connect(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.execute(SCHEMA)
        conn.execute(META_SCHEMA)


def _row_to_contest(row: sqlite3.Row) -> Contest:
    return Contest(
        id=row["id"],
        platform=row["platform"],
        name=row["name"],
        start_time=datetime.fromisoformat(row["start_time"]),
        end_time=datetime.fromisoformat(row["end_time"]),
        url=row["url"],
    )


def upsert_contest(contest: Contest, db_path: Path = DB_PATH) -> None:
    """Insert or refresh contest details without touching its sync state."""
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO contests (id, platform, name, start_time, end_time, url)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                start_time = excluded.start_time,
                end_time = excluded.end_time,
                url = excluded.url
            """,
            (
                contest.id,
                contest.platform,
                contest.name,
                contest.start_time.isoformat(),
                contest.end_time.isoformat(),
                contest.url,
            ),
        )


def get_contest(contest_id: str, db_path: Path = DB_PATH) -> Contest | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM contests WHERE id = ?", (contest_id,)).fetchone()
    return _row_to_contest(row) if row else None


def is_synced(contest_id: str, db_path: Path = DB_PATH) -> bool:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT calendar_event_id FROM contests WHERE id = ?", (contest_id,)
        ).fetchone()
    return row is not None and row["calendar_event_id"] is not None


def mark_synced(contest_id: str, calendar_event_id: str, db_path: Path = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE contests SET calendar_event_id = ?, synced_at = ? WHERE id = ?",
            (calendar_event_id, datetime.now(timezone.utc).isoformat(), contest_id),
        )


def get_calendar_event_id(contest_id: str, db_path: Path = DB_PATH) -> str | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT calendar_event_id FROM contests WHERE id = ?", (contest_id,)
        ).fetchone()
    return row["calendar_event_id"] if row else None


def list_contests(db_path: Path = DB_PATH) -> list[Contest]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM contests ORDER BY start_time").fetchall()
    return [_row_to_contest(r) for r in rows]


def synced_contest_ids(db_path: Path = DB_PATH) -> set[str]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id FROM contests WHERE calendar_event_id IS NOT NULL"
        ).fetchall()
    return {r["id"] for r in rows}


def set_last_sync_run(when: datetime, db_path: Path = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('last_sync_run', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (when.isoformat(),),
        )


def last_sync_run(db_path: Path = DB_PATH) -> datetime | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = 'last_sync_run'").fetchone()
    return datetime.fromisoformat(row["value"]) if row else None
