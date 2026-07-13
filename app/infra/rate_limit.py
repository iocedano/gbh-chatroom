from dataclasses import dataclass, field
from time import monotonic


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


@dataclass
class InMemoryRateLimiter:
    max_events: int
    window_seconds: int
    _events_by_key: dict[str, list[float]] = field(default_factory=dict)

    def check(self, key: str) -> RateLimitResult:
        now = monotonic()
        window_started_at = now - self.window_seconds
        events = [event_at for event_at in self._events_by_key.get(key, []) if event_at > window_started_at]

        if len(events) >= self.max_events:
            retry_after = max(1, int(events[0] + self.window_seconds - now) + 1)
            self._events_by_key[key] = events
            return RateLimitResult(allowed=False, retry_after_seconds=retry_after)

        events.append(now)
        self._events_by_key[key] = events
        return RateLimitResult(allowed=True)

    def reset(self) -> None:
        self._events_by_key.clear()
