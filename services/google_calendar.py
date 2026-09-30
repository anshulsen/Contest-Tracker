import base64
import hashlib

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config
from models import Contest

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CALENDAR_ID = "primary"


def _load_saved_credentials() -> Credentials | None:
    """Return valid saved credentials, refreshing them if needed. Never opens a browser."""
    if not config.TOKEN_FILE.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(config.TOKEN_FILE), SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            return None
        config.TOKEN_FILE.write_text(creds.to_json())
        return creds
    return None


def is_connected() -> bool:
    return _load_saved_credentials() is not None


def authenticate(interactive: bool = True) -> Credentials:
    """Reuse the stored token, or run the browser OAuth flow on first use."""
    creds = _load_saved_credentials()
    if creds:
        return creds
    if not interactive:
        raise PermissionError("Not connected to Google Calendar. Run: python sync.py --connect")
    if not config.CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"{config.CREDENTIALS_FILE.name} not found. Download an OAuth Desktop client "
            "from Google Cloud Console and place it in the project root."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(config.CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    config.TOKEN_FILE.write_text(creds.to_json())
    return creds


def get_service(interactive: bool = True):
    return build("calendar", "v3", credentials=authenticate(interactive), cache_discovery=False)


def event_id_for(contest_id: str) -> str:
    """Deterministic Calendar event ID (allowed alphabet: a-v, 0-9) so retries can't duplicate."""
    digest = hashlib.sha1(contest_id.encode()).digest()
    return base64.b32hexencode(digest).decode().lower().rstrip("=")


def build_event(contest: Contest, reminder_minutes: int = config.REMINDER_MINUTES) -> dict:
    description = (
        f"Platform: {contest.platform}\n"
        f"Contest URL: {contest.url}\n\n"
        f"Contest: {contest.name}\n"
        f"Starts: {contest.start_time.isoformat()}\n"
        f"Ends: {contest.end_time.isoformat()}"
    )
    return {
        "id": event_id_for(contest.id),
        "summary": f"[{contest.platform}] {contest.name}",
        "description": description,
        "source": {"title": contest.platform, "url": contest.url},
        "start": {"dateTime": contest.start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": contest.end_time.isoformat(), "timeZone": "UTC"},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": reminder_minutes}],
        },
    }


def create_event(service, contest: Contest, reminder_minutes: int = config.REMINDER_MINUTES) -> str:
    """Create the Calendar event and return its ID.

    An existing event counts as success; a cancelled (deleted) one is restored.
    """
    body = build_event(contest, reminder_minutes)
    try:
        service.events().insert(calendarId=CALENDAR_ID, body=body).execute()
    except HttpError as e:
        if e.resp.status != 409:
            raise
        if get_event(service, body["id"]).get("status") == "cancelled":
            service.events().update(
                calendarId=CALENDAR_ID, eventId=body["id"], body={**body, "status": "confirmed"}
            ).execute()
    return body["id"]


def update_event(service, contest: Contest, reminder_minutes: int = config.REMINDER_MINUTES) -> str:
    """Overwrite an existing event with current contest details (re-creating it if gone)."""
    body = {**build_event(contest, reminder_minutes), "status": "confirmed"}
    try:
        service.events().update(calendarId=CALENDAR_ID, eventId=body["id"], body=body).execute()
    except HttpError as e:
        if e.resp.status not in (404, 410):
            raise
        return create_event(service, contest, reminder_minutes)
    return body["id"]


def get_event(service, event_id: str) -> dict:
    return service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()


def delete_event(service, event_id: str) -> None:
    service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
