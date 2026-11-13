"""The model-call log: claim a call before sending it, enforce caps, and record what happened.

Claiming first means a retried request with the same key never calls the model twice, and a capped call is
recorded with nothing sent.
"""

from datetime import UTC, datetime, time
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.claude_client import Outcome
from app.config import LlmSettings
from app.db import IntakeSession, LlmCall

ClaimKind = Literal["existing", "capped", "claimed"]


def _find(db: Session, session: IntakeSession, purpose: str, key: str) -> LlmCall | None:
    return db.scalar(
        select(LlmCall).where(LlmCall.session_id == session.id, LlmCall.purpose == purpose, LlmCall.request_key == key)
    )


def _calls_since(db: Session, since: datetime, session: IntakeSession | None = None) -> int:
    query = select(func.count()).select_from(LlmCall).where(LlmCall.created_at >= since, LlmCall.status != "capped")
    if session is not None:
        query = query.where(LlmCall.session_id == session.id)
    return int(db.scalar(query) or 0)


def claim(
    db: Session,
    session: IntakeSession,
    purpose: str,
    key: str,
    request: dict[str, Any],
    now: datetime,
    settings: LlmSettings,
) -> tuple[ClaimKind, LlmCall]:
    existing = _find(db, session, purpose, key)
    if existing is not None:
        return "existing", existing

    day_start = datetime.combine(now.astimezone(UTC).date(), time(0, 0), tzinfo=UTC)
    capped = (
        _calls_since(db, session.created_at, session) >= settings.session_cap
        or _calls_since(db, day_start) >= settings.daily_cap
    )
    inserted = db.execute(
        insert(LlmCall)
        .values(
            session_id=session.id,
            purpose=purpose,
            request_key=key,
            status="capped" if capped else "pending",
            model=settings.model,
            request=None if capped else request,
            created_at=now,
            finished_at=now if capped else None,
        )
        .on_conflict_do_nothing(constraint="one_call_per_request")
        .returning(LlmCall.id)
    ).scalar_one_or_none()
    db.commit()

    if inserted is None:  # a concurrent retry claimed it first
        row = _find(db, session, purpose, key)
        assert row is not None
        return "existing", row
    row = db.get(LlmCall, inserted)
    assert row is not None
    return ("capped" if capped else "claimed"), row


def finish(db: Session, call_id: int, outcome: Outcome, now: datetime) -> LlmCall:
    row = db.get(LlmCall, call_id)
    assert row is not None
    row.status = outcome.status
    row.response = outcome.response
    row.result = outcome.result
    row.error = outcome.error
    row.input_tokens = outcome.input_tokens
    row.output_tokens = outcome.output_tokens
    row.latency_ms = outcome.latency_ms
    row.finished_at = now
    db.commit()
    return row


def log_for(db: Session, session: IntakeSession) -> list[LlmCall]:
    return list(db.scalars(select(LlmCall).where(LlmCall.session_id == session.id).order_by(LlmCall.id)))
