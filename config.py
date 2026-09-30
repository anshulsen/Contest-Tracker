import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

REMINDER_MINUTES = int(os.getenv("REMINDER_MINUTES", "30"))
LOCAL_TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))
