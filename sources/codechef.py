from datetime import datetime

import requests

from models import Contest, make_contest_id
from sources.base import HEADERS, REQUEST_TIMEOUT, ContestSource

API_URL = "https://www.codechef.com/api/list/contests/all"
PARAMS = {"sort_by": "START", "sorting_order": "asc", "offset": 0, "mode": "all"}


def parse_contests(payload: dict) -> list[Contest]:
    if "future_contests" not in payload and "present_contests" not in payload:
        raise RuntimeError("CodeChef API error: unexpected response format")

    contests = []
    for item in payload.get("present_contests", []) + payload.get("future_contests", []):
        try:
            contests.append(
                Contest(
                    id=make_contest_id("codechef", item["contest_code"]),
                    platform="CodeChef",
                    name=item["contest_name"],
                    start_time=datetime.fromisoformat(item["contest_start_date_iso"]),
                    end_time=datetime.fromisoformat(item["contest_end_date_iso"]),
                    url=f"https://www.codechef.com/{item['contest_code']}",
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(contests, key=lambda c: c.start_time)


class CodeChefSource(ContestSource):
    platform = "CodeChef"

    def fetch(self) -> list[Contest]:
        response = requests.get(API_URL, params=PARAMS, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return parse_contests(response.json())
