from collections import deque
from datetime import datetime, timedelta


class RateThrottler:
    def __init__(self, per_minute: int, per_hour: int):
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.events = deque()

    def allow(self, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        while self.events and self.events[0] < hour_ago:
            self.events.popleft()
        per_hour_count = len(self.events)
        per_minute_count = sum(ts >= minute_ago for ts in self.events)
        if per_minute_count >= self.per_minute or per_hour_count >= self.per_hour:
            return False
        self.events.append(now)
        return True
