# Contest Tracker

A small personal tool that fetches upcoming programming contests, adds them to **your own Google
Calendar** with a reminder, and shows a simple dashboard. Contests are never added twice.

- Platforms: Codeforces, LeetCode, CodeChef, AtCoder
- Dashboard: Live / Today / Upcoming / Completed, with a **Sync Now** button
- Reminder: 30 minutes before each contest (configurable)
- Runs locally. Your Google login and data stay on your machine.

## Requirements

- Python 3.10+
- A Google account
- Windows is the primary target. The app itself is cross-platform; only `run_sync.bat` and the
  Task Scheduler section are Windows-specific.

## Setup

### 1. Install

```powershell
git clone <this-repo-url>
cd <repo-folder>
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

(macOS/Linux: use `.venv/bin/pip`, `.venv/bin/python`, and `cp`.)

### 2. Create your own Google OAuth credentials (about 5 minutes)

Each person uses their own Google Cloud project, so nothing is shared and no one else can access your calendar.

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. **APIs & Services > Library**: enable **Google Calendar API**.
3. **OAuth consent screen / Google Auth Platform**: choose **External**, fill in an app name and your email.
4. **Audience**: add your own Gmail address under **Test users**. (Without this, Google shows
   `Error 403: access_denied`.)
5. **Credentials > Create credentials > OAuth client ID > Desktop app**, then download the JSON.
6. Save it as `credentials.json` in the project folder. It is git-ignored; never commit it.

### 3. Connect your calendar (once)

```powershell
.venv\Scripts\python sync.py --connect
```

A browser opens. Sign in and allow Calendar access. If Google says the app is unverified, click
**Advanced > Go to ... (unsafe)**. That warning is normal for your own app in testing mode.
This creates `token.json` (also git-ignored).

## Use

```powershell
.venv\Scripts\streamlit run app.py     # dashboard with Sync Now
.venv\Scripts\python sync.py           # sync from the command line
.venv\Scripts\python -m unittest discover -s tests
```

Settings in `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `REMINDER_MINUTES` | `30` | Popup reminder before each contest |
| `TIMEZONE` | `Asia/Kolkata` | Display timezone and what counts as "today" (any IANA name, e.g. `America/New_York`) |

Events are created in your **primary** calendar as `[Platform] Contest Name`, with the contest link in
the description. Each event gets a deterministic ID, so running sync repeatedly (or even losing the
local database) can not create duplicates. If a contest's time or name changes, the existing event is updated.

## Automatic daily sync (Windows Task Scheduler)

`run_sync.bat` runs the sync and appends its output to `data\sync.log`. From PowerShell, in the project folder:

```powershell
$dir = (Get-Location).Path
$action   = New-ScheduledTaskAction -Execute "$dir\run_sync.bat"
$trigger  = New-ScheduledTaskTrigger -Daily -At 9am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName "ContestTrackerSync" -Action $action -Trigger $trigger -Settings $settings
```

- `-StartWhenAvailable` runs the task later if the PC was off at 9 AM.
- Test it now: `Start-ScheduledTask -TaskName "ContestTrackerSync"`, then check `data\sync.log`.
- Remove it: `Unregister-ScheduledTask -TaskName "ContestTrackerSync" -Confirm:$false`.

The scheduled sync never opens a browser. If your Google login has expired, the log says
`Not connected to Google Calendar`; run `python sync.py --connect` again.

## Notes

- While your Google OAuth app is in **Testing** mode, Google expires the login after 7 days, so
  reconnect about weekly. Publishing the app (Audience page) removes this limit if that option is available to you.
- The dashboard listens on `localhost` only (`.streamlit/config.toml`), so other devices on your network can't
  open it. Don't change `server.address` unless you understand the risk: anyone who can reach it can trigger a sync.
- `token.json` gives access to your calendar events. Keep it private and delete it to disconnect
  (you can also revoke access at https://myaccount.google.com/permissions).
- Never commit `.env`, `credentials.json`, `token.json` or `data/*.db` (all in `.gitignore`).
- Add a platform: create a class in `sources/` that implements `ContestSource.fetch()` and register it in
  `default_sources()` in `sync.py`.
- AtCoder comes from [Codolio's](https://codolio.com/event-tracker) unofficial feed
  (`sources/codolio.py`); the other platforms use their own APIs. If a source is down, the rest still sync.
- LeetCode and CodeChef endpoints are unofficial and can change without notice.
- Project layout: `app.py` (UI), `sync.py` (sync logic), `sources/` (one file per platform),
  `services/` (Google Calendar, status logic), `database/` (SQLite), `models/` (`Contest`).
