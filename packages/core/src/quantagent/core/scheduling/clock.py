from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol


class SchedulingClock(Protocol):
    def now(self) -> datetime: ...

    def monotonic(self) -> float: ...


@dataclass
class SystemSchedulingClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic()


@dataclass
class FrozenSchedulingClock:
    current_time: datetime
    current_monotonic: float = 0.0

    def __post_init__(self) -> None:
        if self.current_time.tzinfo is None or self.current_time.utcoffset() is None:
            raise ValueError("current_time must be timezone-aware.")

    def now(self) -> datetime:
        return self.current_time

    def monotonic(self) -> float:
        return self.current_monotonic

    def advance(self, *, seconds: float = 0.0) -> None:
        self.current_time += timedelta(seconds=seconds)
        self.current_monotonic += seconds
