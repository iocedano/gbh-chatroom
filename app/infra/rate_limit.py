from dataclasses import dataclass, field
from time import time
from typing import Literal

from limits import RateLimitItemPerSecond
from limits import storage as limits_storage
from limits import strategies


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


@dataclass
class LimitsRateLimiter:
    max_events: int
    window_seconds: int
    storage_uri: str = "memory://"
    strategy: Literal["fixed-window", "moving-window", "sliding-window-counter"] = "moving-window"
    _storage: limits_storage.Storage = field(init=False, repr=False)
    _limiter: strategies.RateLimiter = field(init=False, repr=False)
    _limit: RateLimitItemPerSecond = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._configure()

    def _configure(self) -> None:
        self._storage = limits_storage.storage_from_string(self.storage_uri)
        self._limiter = self._build_limiter()
        self._limit = RateLimitItemPerSecond(self.max_events, self.window_seconds)

    def _build_limiter(self) -> strategies.RateLimiter:
        if self.strategy == "fixed-window":
            return strategies.FixedWindowRateLimiter(self._storage)
        if self.strategy == "sliding-window-counter":
            return strategies.SlidingWindowCounterRateLimiter(self._storage)
        return strategies.MovingWindowRateLimiter(self._storage)

    def check(self, key: str) -> RateLimitResult:
        if self._limit.amount != self.max_events or self._limit.multiples != self.window_seconds:
            self._limit = RateLimitItemPerSecond(self.max_events, self.window_seconds)

        if self._limiter.hit(self._limit, key):
            return RateLimitResult(allowed=True)

        window_stats = self._limiter.get_window_stats(self._limit, key)
        retry_after = max(1, int(window_stats.reset_time - time()) + 1)
        return RateLimitResult(allowed=False, retry_after_seconds=retry_after)

    def reset(self) -> None:
        self._storage.reset()
        self._configure()


InMemoryRateLimiter = LimitsRateLimiter
