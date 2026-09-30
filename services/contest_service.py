import re
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo

import config
from models import Contest


class Status(str, Enum):
    LIVE = "LIVE"
    TODAY = "TODAY"
    UPCOMING = "UPCOMING"
    COMPLETED = "COMPLETED"


def get_status(contest: Contest, now: datetime | None = None, tz: ZoneInfo = config.LOCAL_TZ) -> Status:
    now = now or datetime.now(timezone.utc)
    if contest.end_time <= now:
        return Status.COMPLETED
    if contest.start_time <= now:
        return Status.LIVE
    if contest.start_time.astimezone(tz).date() == now.astimezone(tz).date():
        return Status.TODAY
    return Status.UPCOMING


def group_by_status(
    contests: list[Contest], now: datetime | None = None, tz: ZoneInfo = config.LOCAL_TZ
) -> dict[Status, list[Contest]]:
    now = now or datetime.now(timezone.utc)
    groups: dict[Status, list[Contest]] = {status: [] for status in Status}
    for contest in contests:
        groups[get_status(contest, now, tz)].append(contest)
    groups[Status.LIVE].sort(key=lambda c: c.end_time)
    groups[Status.TODAY].sort(key=lambda c: c.start_time)
    groups[Status.UPCOMING].sort(key=lambda c: c.start_time)
    groups[Status.COMPLETED].sort(key=lambda c: c.end_time, reverse=True)
    return groups


def escape_markdown(text: str) -> str:
    """Neutralize Markdown/LaTeX/directive syntax in text that comes from external APIs."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>~:$&])", r"\\\1", text)


def local_date(dt: datetime, tz: ZoneInfo = config.LOCAL_TZ) -> date:
    return dt.astimezone(tz).date()


def day_label(day: date, now: datetime | None = None, tz: ZoneInfo = config.LOCAL_TZ) -> str:
    today = (now or datetime.now(timezone.utc)).astimezone(tz).date()
    if day == today:
        return "Today"
    if day == today + timedelta(days=1):
        return "Tomorrow"
    if day == today - timedelta(days=1):
        return "Yesterday"
    return day.strftime("%a, %d %b")


def format_clock(dt: datetime, tz: ZoneInfo = config.LOCAL_TZ) -> str:
    return dt.astimezone(tz).strftime("%I:%M %p")


def format_range(contest: Contest, tz: ZoneInfo = config.LOCAL_TZ) -> str:
    start, end = contest.start_time.astimezone(tz), contest.end_time.astimezone(tz)
    if start.date() == end.date():
        return f"{start:%a, %d %b}, {format_clock(start, tz)} - {format_clock(end, tz)}"
    return f"{start:%a, %d %b %I:%M %p} - {end:%a, %d %b %I:%M %p}"


def time_ago(then: datetime, now: datetime | None = None) -> str:
    seconds = int(((now or datetime.now(timezone.utc)) - then).total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} hr ago"
    return f"{seconds // 86400} days ago"
