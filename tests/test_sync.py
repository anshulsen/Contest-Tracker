import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sync
from database import database as db
from models import Contest, make_contest_id
from sources.base import ContestSource

NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


def contest(source_id: int, start_offset_h: float = 5, name: str = "Round", platform: str = "Codeforces") -> Contest:
    start = NOW + timedelta(hours=start_offset_h)
    return Contest(
        make_contest_id(platform, source_id), platform, f"{name} {source_id}",
        start, start + timedelta(hours=2), f"https://x/{source_id}",
    )


class FakeSource(ContestSource):
    def __init__(self, platform: str, contests: list[Contest] | None = None, error: Exception | None = None):
        self.platform, self._contests, self._error = platform, contests or [], error

    def fetch(self) -> list[Contest]:
        if self._error:
            raise self._error
        return self._contests


class SyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "t.db"
        self.created: list[str] = []
        self.updated: list[str] = []

        def fake_create(service, c, *a):
            self.created.append(c.id)
            return gc_id(c)

        def fake_update(service, c, *a):
            self.updated.append(c.id)
            return gc_id(c)

        def gc_id(c):
            return "evt-" + c.id

        patches = [
            patch("sync.gc.create_event", fake_create),
            patch("sync.gc.update_event", fake_update),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._tmp.cleanup)

    def run_sync(self, sources):
        return sync.sync_contests(sources, calendar=object(), db_path=self.path, now=NOW)

    def test_second_sync_creates_nothing(self) -> None:
        sources = [FakeSource("Codeforces", [contest(1), contest(2)])]
        first = self.run_sync(sources)
        second = self.run_sync(sources)
        self.assertEqual((first.added, first.skipped), (2, 0))
        self.assertEqual((second.added, second.skipped), (0, 2))
        self.assertEqual(self.created, ["codeforces:1", "codeforces:2"])

    def test_filters_past_and_far_future(self) -> None:
        sources = [FakeSource("Codeforces", [contest(1, -10), contest(2, 24 * 60), contest(3, 1), contest(4, -1)])]
        result = self.run_sync(sources)
        # 1 is over, 2 is beyond the window, 3 is upcoming, 4 is live (started 1h ago, ends in 1h)
        self.assertEqual(sorted(self.created), ["codeforces:3", "codeforces:4"])
        self.assertEqual(result.fetched, 2)

    def test_duplicates_across_sources_collapse(self) -> None:
        sources = [FakeSource("Codeforces", [contest(1)]), FakeSource("Codeforces", [contest(1)])]
        result = self.run_sync(sources)
        self.assertEqual((result.fetched, result.added), (1, 1))

    def test_failing_source_does_not_stop_others(self) -> None:
        sources = [
            FakeSource("CodeChef", error=RuntimeError("API unavailable")),
            FakeSource("Codeforces", [contest(1)]),
        ]
        result = self.run_sync(sources)
        self.assertEqual(result.added, 1)
        self.assertEqual(result.source_errors, {"CodeChef": "API unavailable"})
        self.assertEqual(result.sources_ok, ["Codeforces"])

    def test_calendar_failure_is_not_recorded_as_synced(self) -> None:
        with patch("sync.gc.create_event", side_effect=RuntimeError("boom")):
            result = self.run_sync([FakeSource("Codeforces", [contest(1)])])
        self.assertEqual(result.added, 0)
        self.assertIn("Round 1", result.failed)
        self.assertFalse(db.is_synced("codeforces:1", self.path))
        retry = self.run_sync([FakeSource("Codeforces", [contest(1)])])
        self.assertEqual(retry.added, 1)

    def test_changed_time_updates_event_once(self) -> None:
        self.run_sync([FakeSource("Codeforces", [contest(1, 5)])])
        moved = [contest(1, 8)]
        result = self.run_sync([FakeSource("Codeforces", moved)])
        again = self.run_sync([FakeSource("Codeforces", moved)])
        self.assertEqual((result.updated, result.added), (1, 0))
        self.assertEqual((again.updated, again.skipped), (0, 1))
        self.assertEqual(self.updated, ["codeforces:1"])

    def test_last_sync_run_recorded_only_if_a_source_succeeded(self) -> None:
        self.run_sync([FakeSource("CodeChef", error=RuntimeError("down"))])
        self.assertIsNone(db.last_sync_run(self.path))
        self.run_sync([FakeSource("Codeforces", [])])
        self.assertEqual(db.last_sync_run(self.path), NOW)

    def test_not_connected_reports_calendar_error(self) -> None:
        with patch("sync.gc.get_service", side_effect=PermissionError("Not connected")):
            result = sync.sync_contests(
                [FakeSource("Codeforces", [contest(1)])], db_path=self.path, now=NOW
            )
        self.assertEqual(result.calendar_error, "Not connected")
        self.assertEqual(result.added, 0)


if __name__ == "__main__":
    unittest.main()
