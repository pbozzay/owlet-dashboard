from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable


class RateLimiter:
    """In-memory sliding window. Single-process by design (one container)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, *, max_hits: int, window_seconds: float) -> bool:
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= window_seconds:
            hits.popleft()
        if len(hits) >= max_hits:
            return False
        hits.append(now)
        return True
