import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources.codeforces import parse_contests

PAYLOAD = {
    "status": "OK",
    "result": [
        {"id": 2, "name": "Finished", "phase": "FINISHED", "startTimeSeconds": 1000, "durationSeconds": 7200},
        {"id": 3, "name": "Later", "phase": "BEFORE", "startTimeSeconds": 1893456000, "durationSeconds": 9000},
        {"id": 4, "name": "Running", "phase": "CODING", "startTimeSeconds": 1893000000, "durationSeconds": 7200},
        {"id": 5, "name": "No start", "phase": "BEFORE", "durationSeconds": 7200},
    ],
}


class CodeforcesParseTests(unittest.TestCase):
    def test_keeps_only_active_contests_sorted(self) -> None:
        contests = parse_contests(PAYLOAD)
        self.assertEqual([c.name for c in contests], ["Running", "Later"])

    def test_normalization(self) -> None:
        later = parse_contests(PAYLOAD)[1]
        self.assertEqual(later.id, "codeforces:3")
        self.assertEqual(later.platform, "Codeforces")
        self.assertEqual(later.start_time, datetime(2030, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(later.end_time - later.start_time, timedelta(seconds=9000))
        self.assertEqual(later.url, "https://codeforces.com/contest/3")

    def test_api_failure_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            parse_contests({"status": "FAILED", "comment": "down"})


if __name__ == "__main__":
    unittest.main()
