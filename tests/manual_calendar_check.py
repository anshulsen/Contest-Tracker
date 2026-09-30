"""Manual check: creates ONE test event, verifies it, then deletes it (pass --keep to keep it)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from models import Contest, make_contest_id
from services import google_calendar as gc


def main() -> None:
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
    contest = Contest(
        id=make_contest_id("test", f"calendar-check-{int(datetime.now().timestamp())}"),
        platform="Test",
        name="Contest Tracker Calendar Check",
        start_time=start,
        end_time=start + timedelta(hours=2),
        url="https://example.com/contest",
    )

    service = gc.get_service()
    print("OAuth + Calendar access: OK")

    event_id = gc.create_event(service, contest)
    event_id_again = gc.create_event(service, contest)
    event = gc.get_event(service, event_id)
    print("Event created:", event.get("htmlLink"))

    checks = {
        "status confirmed": event.get("status") == "confirmed",
        "title": event["summary"] == "[Test] Contest Tracker Calendar Check",
        "start time": datetime.fromisoformat(event["start"]["dateTime"]) == contest.start_time,
        "end time": datetime.fromisoformat(event["end"]["dateTime"]) == contest.end_time,
        "reminder": event["reminders"]["overrides"] == [{"method": "popup", "minutes": config.REMINDER_MINUTES}],
        "url in description": contest.url in event["description"],
        "retry does not duplicate": event_id == event_id_again,
    }
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    print("  Event start as stored:", event["start"])

    if "--keep" not in sys.argv:
        gc.delete_event(service, event_id)
        print("Test event deleted.")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
