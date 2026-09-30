from datetime import datetime, timezone
from itertools import groupby

import streamlit as st

from database import database as db
from models import Contest
from services import google_calendar as gc
from services.contest_service import (
    Status,
    day_label,
    format_clock,
    format_range,
    group_by_status,
    local_date,
    time_ago,
)
from sync import SyncResult, sync_contests

COMPLETED_LIMIT = 10

SECTIONS = [
    (Status.LIVE, "🔴", "LIVE NOW", "red"),
    (Status.TODAY, "📅", "TODAY", "orange"),
    (Status.UPCOMING, "🔜", "UPCOMING", "blue"),
    (Status.COMPLETED, "✅", "COMPLETED", "gray"),
]
EMPTY_TEXT = {
    Status.LIVE: "No contests are running right now.",
    Status.TODAY: "No more contests today.",
    Status.UPCOMING: "No upcoming contests. Try Sync Now.",
    Status.COMPLETED: "No completed contests yet.",
}


def render_sync_result(result: SyncResult) -> None:
    lines = [f"✓ {p}" for p in result.sources_ok]
    lines += [f"✗ {p}: {e}" for p, e in result.source_errors.items()]
    lines.append(f"✓ {result.fetched} contests fetched")
    lines.append(f"✓ {result.added} new contests added")
    if result.updated:
        lines.append(f"✓ {result.updated} existing events updated")
    lines.append(f"⏭ {result.skipped} already synced")
    lines += [f"✗ Calendar: {name}: {e}" for name, e in result.failed.items()]
    if result.calendar_error:
        lines.append(f"✗ Calendar: {result.calendar_error}")

    has_errors = bool(result.source_errors or result.failed or result.calendar_error)
    box = st.warning if has_errors else st.success
    box("  \n".join(lines))


def render_card(contest: Contest, status: Status, color: str, synced: bool, now: datetime) -> None:
    with st.container(border=True):
        info, action = st.columns([5, 1], vertical_alignment="center")
        info.markdown(f"**{contest.name}**  :{color}-badge[{status.value}]")
        info.caption(f"{contest.platform} · {format_range(contest)}")
        if status is Status.LIVE:
            info.caption(f"Started {format_clock(contest.start_time)} · ends {format_clock(contest.end_time)}")
        info.caption("📅 In Google Calendar" if synced else "⏳ Not in Google Calendar")
        action.link_button("Open", contest.url)


def render_section(status: Status, title: str, icon: str, color: str, contests: list[Contest],
                   synced_ids: set[str], now: datetime) -> None:
    st.subheader(f"{icon} {title}")
    if not contests:
        st.caption(EMPTY_TEXT[status])
        return

    if status is Status.UPCOMING:
        for day, day_contests in groupby(contests, key=lambda c: local_date(c.start_time)):
            st.markdown(f"**{day_label(day, now)}**")
            for contest in day_contests:
                render_card(contest, status, color, contest.id in synced_ids, now)
        return

    shown = contests[:COMPLETED_LIMIT] if status is Status.COMPLETED else contests
    for contest in shown:
        render_card(contest, status, color, contest.id in synced_ids, now)
    if len(shown) < len(contests):
        st.caption(f"Showing {len(shown)} most recent of {len(contests)}.")


def connect_calendar() -> None:
    try:
        gc.authenticate()
    except FileNotFoundError as e:
        st.error(str(e))
    except Exception as e:
        st.error(f"Google authentication failed: {e}")
    else:
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="Contest Tracker", page_icon="🏆")
    st.title("🏆 Contest Tracker")
    db.init_db()

    button_col, info_col = st.columns([1, 2], vertical_alignment="center")
    if button_col.button("🔄 Sync Now", type="primary"):
        with st.spinner("Syncing contests..."):
            st.session_state["sync_result"] = sync_contests()

    now = datetime.now(timezone.utc)
    last_sync = db.last_sync_run()
    info_col.caption(f"Last sync: {time_ago(last_sync, now)}" if last_sync else "Never synced")

    if not gc.is_connected():
        st.warning("Google Calendar is not connected. Contests can be viewed, but not added to your calendar.")
        if st.button("Connect Google Calendar"):
            connect_calendar()

    if "sync_result" in st.session_state:
        render_sync_result(st.session_state["sync_result"])

    groups = group_by_status(db.list_contests(), now)
    synced_ids = db.synced_contest_ids()
    for status, icon, title, color in SECTIONS:
        render_section(status, title, icon, color, groups[status], synced_ids, now)


main()
