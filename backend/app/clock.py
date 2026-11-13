"""The current time, as a dependency so tests can pin it."""

from datetime import UTC, datetime


def get_now() -> datetime:
    return datetime.now(UTC)
