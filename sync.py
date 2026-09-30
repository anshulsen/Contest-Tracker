import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from database import database as db
from models import Contest
from services import google_calendar as gc
from sources.base import ContestSource
from sources.codechef import CodeChefSource
from sources.codeforces import CodeforcesSource
from sources.codolio import CodolioSource
from sources.leetcode import LeetCodeSource

SYNC_WINDOW_DAYS = 30


def default_sources() -> list[ContestSource]:
    return [
        CodeforcesSource(),
        LeetCodeSource(),
        CodeChefSource(),
        CodolioSource("atcoder", "AtCoder"),
    ]


@dataclass
class SyncResult:
    fetched: int = 0
    added: int = 0
    updated: int = 0
    skipped: int = 0
    source_errors: dict[str, str] = field(default_factory=dict)
    sources_ok: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    calendar_error: str | None = None

    def lines(self) -> list[str]:
        out = [f"OK   {p}" for p in self.sources_ok]
        out += [f"FAIL {p}: {e}" for p, e in self.source_errors.items()]
        out.append(f"{self.fetched} contests fetched")
        out.append(f"{self.added} new contests added")
        if self.updated:
            out.append(f"{self.updated} existing events updated")
        out.append(f"{self.skipped} already synced")
        out += [f"FAIL calendar {name}: {e}" for name, e in self.failed.items()]
        if self.calendar_error:
            out.append(f"FAIL calendar: {self.calendar_error}")
        return out


def fetch_all(sources: list[ContestSource], result: SyncResult) -> list[Contest]:
    contests: dict[str, Contest] = {}
    for source in sources:
        try:
            fetched = source.fetch()
        except Exception as e:
            result.source_errors[source.platform] = str(e) or type(e).__name__
            continue
        result.sources_ok.append(source.platform)
        for contest in fetched:
            contests.setdefault(contest.id, contest)
    return list(contests.values())


def is_relevant(contest: Contest, now: datetime) -> bool:
    return contest.end_time > now and contest.start_time <= now + timedelta(days=SYNC_WINDOW_DAYS)


def has_changed(old: Contest, new: Contest) -> bool:
    return (old.name, old.start_time, old.end_time, old.url) != (
        new.name,
        new.start_time,
        new.end_time,
        new.url,
    )


def sync_contests(
    sources: list[ContestSource] | None = None,
    calendar=None,
    db_path: Path = db.DB_PATH,
    now: datetime | None = None,
) -> SyncResult:
    """Fetch contests, add missing ones to Google Calendar, and record them in SQLite."""
    now = now or datetime.now(timezone.utc)
    result = SyncResult()
    db.init_db(db_path)
    _run_sync(result, sources or default_sources(), calendar, db_path, now)
    if result.sources_ok:
        db.set_last_sync_run(now, db_path)
    return result


def _run_sync(
    result: SyncResult,
    sources: list[ContestSource],
    calendar,
    db_path: Path,
    now: datetime,
) -> None:
    contests = [
        c for c in fetch_all(sources, result) if is_relevant(c, now)
    ]
    result.fetched = len(contests)

    to_create: list[Contest] = []
    to_update: list[Contest] = []
    for contest in contests:
        existing = db.get_contest(contest.id, db_path)
        synced = db.is_synced(contest.id, db_path)
        if synced and existing and has_changed(existing, contest):
            to_update.append(contest)
            continue
        db.upsert_contest(contest, db_path)
        if synced:
            result.skipped += 1
        else:
            to_create.append(contest)

    if not (to_create or to_update):
        return

    try:
        service = calendar or gc.get_service(interactive=False)
    except Exception as e:
        result.calendar_error = str(e) or type(e).__name__
        return

    for contest in to_create:
        try:
            event_id = gc.create_event(service, contest)
            db.mark_synced(contest.id, event_id, db_path)
            result.added += 1
        except Exception as e:
            result.failed[contest.name] = str(e) or type(e).__name__

    for contest in to_update:
        try:
            gc.update_event(service, contest)
            db.upsert_contest(contest, db_path)
            result.updated += 1
        except Exception as e:
            result.failed[contest.name] = str(e) or type(e).__name__


def main() -> int:
    if "--connect" in sys.argv:
        gc.authenticate()
        print("Connected to Google Calendar.")
        return 0
    result = sync_contests()
    print("\n".join(result.lines()))
    return 1 if (result.calendar_error or result.failed) else 0


if __name__ == "__main__":
    sys.exit(main())
