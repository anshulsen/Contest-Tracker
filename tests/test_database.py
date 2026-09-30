import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import database as db
from models import Contest, make_contest_id


def sample(source_id: int = 1, name: str = "Round 1") -> Contest:
    start = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
    return Contest(
        id=make_contest_id("Codeforces", source_id),
        platform="Codeforces",
        name=name,
        start_time=start,
        end_time=start + timedelta(hours=2),
        url=f"https://codeforces.com/contest/{source_id}",
    )


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "test.db"
        db.init_db(self.path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_naive_datetime_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Contest("x:1", "x", "n", datetime(2030, 1, 1), datetime(2030, 1, 2), "u")

    def test_end_before_start_rejected(self) -> None:
        s = datetime(2030, 1, 1, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            Contest("x:1", "x", "n", s, s, "u")

    def test_roundtrip_preserves_timezone(self) -> None:
        c = sample()
        db.upsert_contest(c, self.path)
        [loaded] = db.list_contests(self.path)
        self.assertEqual(loaded, c)
        self.assertIsNotNone(loaded.start_time.tzinfo)

    def test_new_contest_is_not_synced(self) -> None:
        db.upsert_contest(sample(), self.path)
        self.assertFalse(db.is_synced("codeforces:1", self.path))

    def test_mark_synced(self) -> None:
        db.upsert_contest(sample(), self.path)
        db.mark_synced("codeforces:1", "evt123", self.path)
        self.assertTrue(db.is_synced("codeforces:1", self.path))
        self.assertEqual(db.get_calendar_event_id("codeforces:1", self.path), "evt123")

    def test_last_sync_run_roundtrip(self) -> None:
        self.assertIsNone(db.last_sync_run(self.path))
        first = datetime(2030, 1, 1, tzinfo=timezone.utc)
        db.set_last_sync_run(first, self.path)
        db.set_last_sync_run(first + timedelta(hours=1), self.path)
        self.assertEqual(db.last_sync_run(self.path), first + timedelta(hours=1))

    def test_upsert_keeps_sync_state_and_updates_details(self) -> None:
        db.upsert_contest(sample(), self.path)
        db.mark_synced("codeforces:1", "evt123", self.path)
        db.upsert_contest(sample(name="Renamed"), self.path)
        [loaded] = db.list_contests(self.path)
        self.assertEqual(loaded.name, "Renamed")
        self.assertTrue(db.is_synced("codeforces:1", self.path))

    def test_no_duplicate_rows(self) -> None:
        for _ in range(3):
            db.upsert_contest(sample(), self.path)
        self.assertEqual(len(db.list_contests(self.path)), 1)


if __name__ == "__main__":
    unittest.main()
