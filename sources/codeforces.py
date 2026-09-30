from datetime import datetime, timedelta, timezone

import requests

from models import Contest, make_contest_id
from sources.base import REQUEST_TIMEOUT, ContestSource

API_URL = "https://codeforces.com/api/contest.list"
ACTIVE_PHASES = {"BEFORE", "CODING"}


def parse_contests(payload: dict) -> list[Contest]:
    if payload.get("status") != "OK":
        raise RuntimeError(f"Codeforces API error: {payload.get('comment', 'unknown')}")

    contests = []
    for item in payload["result"]:
        if item.get("phase") not in ACTIVE_PHASES or "startTimeSeconds" not in item:
            continue
        start = datetime.fromtimestamp(item["startTimeSeconds"], tz=timezone.utc)
        contests.append(
            Contest(
                id=make_contest_id("codeforces", item["id"]),
                platform="Codeforces",
                name=item["name"],
                start_time=start,
                end_time=start + timedelta(seconds=item["durationSeconds"]),
                url=f"https://codeforces.com/contest/{item['id']}",
            )
        )
    return sorted(contests, key=lambda c: c.start_time)


class CodeforcesSource(ContestSource):
    platform = "Codeforces"

    def fetch(self) -> list[Contest]:
        response = requests.get(API_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return parse_contests(response.json())
