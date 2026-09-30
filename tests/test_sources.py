import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import codechef, codolio, leetcode

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


class LeetCodeTests(unittest.TestCase):
    PAYLOAD = {
        "data": {
            "allContests": [
                {"title": "Weekly Contest 523", "titleSlug": "weekly-contest-523", "startTime": 1791685800, "duration": 5400},
                {"title": "Old", "titleSlug": "weekly-contest-1", "startTime": 1000, "duration": 5400},
                {"title": "Broken", "titleSlug": "x"},
            ]
        }
    }

    def test_parse(self) -> None:
        [c] = leetcode.parse_contests(self.PAYLOAD, now=NOW)
        self.assertEqual(c.id, "leetcode:weekly-contest-523")
        self.assertEqual(c.platform, "LeetCode")
        self.assertEqual(c.start_time, datetime.fromtimestamp(1791685800, timezone.utc))
        self.assertEqual(c.end_time - c.start_time, timedelta(seconds=5400))
        self.assertEqual(c.url, "https://leetcode.com/contest/weekly-contest-523/")

    def test_errors_raise(self) -> None:
        with self.assertRaises(RuntimeError):
            leetcode.parse_contests({"errors": [{"message": "bad"}]})


class CodeChefTests(unittest.TestCase):
    PAYLOAD = {
        "present_contests": [],
        "future_contests": [
            {
                "contest_code": "START258",
                "contest_name": "Starters 258",
                "contest_start_date_iso": "2026-09-30T20:00:00+05:30",
                "contest_end_date_iso": "2026-09-30T22:00:00+05:30",
            },
            {"contest_code": "BROKEN"},
        ],
    }

    def test_parse(self) -> None:
        [c] = codechef.parse_contests(self.PAYLOAD)
        self.assertEqual(c.id, "codechef:START258")
        self.assertEqual(c.start_time, datetime(2026, 9, 30, 14, 30, tzinfo=timezone.utc))
        self.assertEqual(c.end_time, datetime(2026, 9, 30, 16, 30, tzinfo=timezone.utc))
        self.assertEqual(c.url, "https://www.codechef.com/START258")

    def test_unexpected_format_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            codechef.parse_contests({"message": "blocked"})


class CodolioTests(unittest.TestCase):
    PAYLOAD = {
        "status": {"success": True},
        "data": [
            {
                "platform": "atcoder", "contestCode": "abc480", "contestName": "AtCoder Beginner Contest 480",
                "contestStartDate": "2026-10-17T12:00:00.000Z", "contestEndDate": "2026-10-17T13:40:00.000Z",
                "contestUrl": "https://atcoder.jp/contests/abc480",
            },
            {
                "platform": "codeforces", "contestCode": "2270", "contestName": "Phantom",
                "contestStartDate": "2026-10-11T18:35:00.000Z", "contestEndDate": "2026-10-11T21:05:00.000Z",
                "contestUrl": "https://codeforces.com/contest/2270",
            },
        ],
    }

    def test_filters_by_platform_and_normalizes(self) -> None:
        [c] = codolio.parse_contests(self.PAYLOAD, "atcoder", "AtCoder")
        self.assertEqual(c.id, "atcoder:abc480")
        self.assertEqual(c.platform, "AtCoder")
        self.assertEqual(c.start_time, datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(c.end_time, datetime(2026, 10, 17, 13, 40, tzinfo=timezone.utc))
        self.assertEqual(c.url, "https://atcoder.jp/contests/abc480")

    def test_failure_response_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            codolio.parse_contests({"status": {"success": False, "message": "down"}}, "atcoder", "AtCoder")


if __name__ == "__main__":
    unittest.main()
