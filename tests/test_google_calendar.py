import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import Contest
from services.google_calendar import build_event, event_id_for


def sample() -> Contest:
    start = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
    return Contest("codeforces:1", "Codeforces", "Round 1", start, start + timedelta(hours=2), "https://cf/1")


class EventTests(unittest.TestCase):
    def test_event_id_is_valid_and_stable(self) -> None:
        eid = event_id_for("codeforces:1")
        self.assertRegex(eid, r"^[a-v0-9]{5,1024}$")
        self.assertEqual(eid, event_id_for("codeforces:1"))
        self.assertNotEqual(eid, event_id_for("codeforces:2"))

    def test_event_body(self) -> None:
        body = build_event(sample(), reminder_minutes=45)
        self.assertEqual(body["summary"], "[Codeforces] Round 1")
        self.assertIn("https://cf/1", body["description"])
        self.assertEqual(body["reminders"]["overrides"], [{"method": "popup", "minutes": 45}])
        self.assertEqual(body["start"]["dateTime"], "2030-01-01T12:00:00+00:00")
        self.assertFalse(body["reminders"]["useDefault"])


if __name__ == "__main__":
    unittest.main()
