import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import Contest
import re

from services.contest_service import (
    Status,
    day_label,
    escape_markdown,
    format_range,
    get_status,
    group_by_status,
    time_ago,
)

IST = ZoneInfo("Asia/Kolkata")
# 2030-01-01 10:00 IST
NOW = datetime(2030, 1, 1, 4, 30, tzinfo=timezone.utc)


def make(start: datetime, hours: float = 2, cid: str = "x:1") -> Contest:
    return Contest(cid, "X", "Name", start, start + timedelta(hours=hours), "https://x")


class StatusTests(unittest.TestCase):
    def status(self, start: datetime, hours: float = 2) -> Status:
        return get_status(make(start, hours), NOW, IST)

    def test_live(self) -> None:
        self.assertEqual(self.status(NOW - timedelta(minutes=30)), Status.LIVE)

    def test_live_boundaries(self) -> None:
        self.assertEqual(self.status(NOW), Status.LIVE)
        self.assertEqual(self.status(NOW - timedelta(hours=2)), Status.COMPLETED)

    def test_today_later_same_local_day(self) -> None:
        self.assertEqual(self.status(NOW + timedelta(hours=6)), Status.TODAY)

    def test_today_uses_local_timezone_not_utc(self) -> None:
        # 20:00 UTC Jan 1 = 01:30 IST Jan 2 -> tomorrow locally although the same day in UTC
        self.assertEqual(self.status(datetime(2030, 1, 1, 20, 0, tzinfo=timezone.utc)), Status.UPCOMING)
        # 18:00 UTC Dec 31 = 23:30 IST Dec 31 (already ended), 18:29 UTC Jan 1 = 23:59 IST Jan 1 -> today
        self.assertEqual(self.status(datetime(2030, 1, 1, 18, 29, tzinfo=timezone.utc)), Status.TODAY)

    def test_upcoming(self) -> None:
        self.assertEqual(self.status(NOW + timedelta(days=3)), Status.UPCOMING)

    def test_completed(self) -> None:
        self.assertEqual(self.status(NOW - timedelta(days=1)), Status.COMPLETED)

    def test_contest_started_yesterday_still_running_is_live(self) -> None:
        self.assertEqual(self.status(NOW - timedelta(hours=20), hours=48), Status.LIVE)


class GroupingTests(unittest.TestCase):
    def test_groups_and_ordering(self) -> None:
        contests = [
            make(NOW + timedelta(days=2), cid="a"),
            make(NOW + timedelta(days=1), cid="b"),
            make(NOW - timedelta(days=3), cid="c"),
            make(NOW - timedelta(days=1), cid="d"),
            make(NOW - timedelta(minutes=10), cid="e"),
            make(NOW + timedelta(hours=1), cid="f"),
        ]
        groups = group_by_status(contests, NOW, IST)
        self.assertEqual([c.id for c in groups[Status.UPCOMING]], ["b", "a"])
        self.assertEqual([c.id for c in groups[Status.COMPLETED]], ["d", "c"])
        self.assertEqual([c.id for c in groups[Status.LIVE]], ["e"])
        self.assertEqual([c.id for c in groups[Status.TODAY]], ["f"])


class FormatTests(unittest.TestCase):
    def test_day_label(self) -> None:
        today = NOW.astimezone(IST).date()
        self.assertEqual(day_label(today, NOW, IST), "Today")
        self.assertEqual(day_label(today + timedelta(days=1), NOW, IST), "Tomorrow")
        self.assertEqual(day_label(today + timedelta(days=5), NOW, IST), "Sun, 06 Jan")

    def test_format_range_same_day_in_local_tz(self) -> None:
        c = make(datetime(2030, 1, 1, 14, 35, tzinfo=timezone.utc), hours=3)  # 20:05 -> 23:05 IST
        self.assertEqual(format_range(c, IST), "Tue, 01 Jan, 08:05 PM - 11:05 PM")

    def test_format_range_multi_day(self) -> None:
        c = make(datetime(2030, 1, 1, 14, 35, tzinfo=timezone.utc), hours=30)
        self.assertEqual(format_range(c, IST), "Tue, 01 Jan 08:05 PM - Thu, 03 Jan 02:05 AM")

    def test_escape_markdown_neutralizes_injection(self) -> None:
        hostile = "[click](http://evil.com) ![x](http://track.com/p.png) :red[hi] $$x$$ <b>a</b> `c` **b**"
        escaped = escape_markdown(hostile)
        self.assertIsNone(re.search(r"(?<!\\)[\[\]()<>`*$:]", escaped))

    def test_escape_markdown_keeps_text_readable(self) -> None:
        self.assertEqual(escape_markdown("Round 1"), "Round 1")

    def test_time_ago(self) -> None:
        self.assertEqual(time_ago(NOW - timedelta(seconds=10), NOW), "just now")
        self.assertEqual(time_ago(NOW - timedelta(minutes=2), NOW), "2 min ago")
        self.assertEqual(time_ago(NOW - timedelta(hours=3), NOW), "3 hr ago")
        self.assertEqual(time_ago(NOW - timedelta(days=2), NOW), "2 days ago")


if __name__ == "__main__":
    unittest.main()
