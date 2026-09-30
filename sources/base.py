from abc import ABC, abstractmethod

from models import Contest

REQUEST_TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (personal contest tracker)"}


class ContestSource(ABC):
    """A platform adapter. Subclasses convert platform data into `Contest`."""

    platform: str

    @abstractmethod
    def fetch(self) -> list[Contest]:
        """Return current and upcoming contests. Raise on failure."""
