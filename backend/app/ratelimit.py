"""A per-client limit on starting sessions, so one address can't fill the database or burn the model budget.

In memory, which suits the demo's single API instance. The client address is the right-most X-Forwarded-For
entry (the one Railway's proxy adds; anything to its left came from the client and can be forged), falling back
to the socket address.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request

WINDOW = timedelta(hours=1)


def client_address(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class SessionLimiter:
    def __init__(self, per_hour: int) -> None:
        self.per_hour = per_hour
        self._starts: dict[str, deque[datetime]] = defaultdict(deque)

    def allow(self, client: str, now: datetime) -> bool:
        """Record a start for `client` and say whether it is within the limit."""
        if self.per_hour <= 0:
            return True
        starts = self._starts[client]
        while starts and starts[0] <= now - WINDOW:
            starts.popleft()
        if len(starts) >= self.per_hour:
            return False
        starts.append(now)
        return True
