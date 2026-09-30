from datetime import datetime, timedelta, timezone

import requests

from models import Contest, make_contest_id
from sources.base import HEADERS, REQUEST_TIMEOUT, ContestSource

API_URL = "https://leetcode.com/graphql"
QUERY = "{ allContests { title titleSlug startTime duration } }"


def parse_contests(payload: dict, now: datetime | None = None) -> list[Contest]:
    if payload.get("errors") or "data" not in payload:
        raise RuntimeError(f"LeetCode API error: {payload.get('errors', 'no data')}")

    now = now or datetime.now(timezone.utc)
    contests = []
    for item in payload["data"]["allContests"]:
        try:
            start = datetime.fromtimestamp(item["startTime"], tz=timezone.utc)
            contest = Contest(
                id=make_contest_id("leetcode", item["titleSlug"]),
                platform="LeetCode",
                name=item["title"],
                start_time=start,
                end_time=start + timedelta(seconds=item["duration"]),
                url=f"https://leetcode.com/contest/{item['titleSlug']}/",
            )
        except (KeyError, TypeError, ValueError):
            continue
        if contest.end_time > now:
            contests.append(contest)
    return sorted(contests, key=lambda c: c.start_time)


class LeetCodeSource(ContestSource):
    platform = "LeetCode"

    def fetch(self) -> list[Contest]:
        response = requests.post(
            API_URL,
            json={"query": QUERY},
            headers={**HEADERS, "Referer": "https://leetcode.com/contest/"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return parse_contests(response.json())
