from datetime import datetime

import requests

from models import Contest, make_contest_id
from sources.base import HEADERS, REQUEST_TIMEOUT, ContestSource

API_URL = "https://node.codolio.com/api/contest-calendar/v1/all/get-upcoming-contests"


def parse_contests(payload: dict, platform_key: str, platform_label: str) -> list[Contest]:
    if not payload.get("status", {}).get("success") or not isinstance(payload.get("data"), list):
        raise RuntimeError(f"Codolio API error: {payload.get('status', {}).get('message', 'bad response')}")

    contests = []
    for item in payload["data"]:
        if str(item.get("platform", "")).strip().lower() != platform_key:
            continue
        try:
            contests.append(
                Contest(
                    id=make_contest_id(platform_key, item["contestCode"]),
                    platform=platform_label,
                    name=item["contestName"],
                    start_time=datetime.fromisoformat(item["contestStartDate"]),
                    end_time=datetime.fromisoformat(item["contestEndDate"]),
                    url=item["contestUrl"],
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(contests, key=lambda c: c.start_time)


class CodolioSource(ContestSource):
    """One platform's contests from Codolio's aggregated (unofficial) feed."""

    def __init__(self, platform_key: str, platform_label: str) -> None:
        self.platform_key = platform_key
        self.platform = platform_label

    def fetch(self) -> list[Contest]:
        response = requests.get(API_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return parse_contests(response.json(), self.platform_key, self.platform)
