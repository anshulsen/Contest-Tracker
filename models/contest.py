from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Contest:
    """Common contest model. `id` is the stable key: "<platform>:<source id>"."""

    id: str
    platform: str
    name: str
    start_time: datetime
    end_time: datetime
    url: str

    def __post_init__(self) -> None:
        for field_name in ("start_time", "end_time"):
            value = getattr(self, field_name)
            if value.tzinfo is None:
                raise ValueError(f"{field_name} must be timezone-aware")
            object.__setattr__(self, field_name, value.astimezone(timezone.utc))
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")


def make_contest_id(platform: str, source_id: str | int) -> str:
    return f"{platform.lower()}:{source_id}"
