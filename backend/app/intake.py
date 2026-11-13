"""Intake sessions: create, resume, connect Health, and save answers safely on retry."""

import uuid
from datetime import datetime, timedelta
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.answers import InvalidAnswer, validate
from app.config import Settings
from app.db import HealthSummaryRow, IntakeAnswer, IntakeSession
from app.health.members import MEMBER_IDS, load_member
from app.health.models import MemberId, resolve
from app.health.summary import HealthSummaryV1, build_summary
from app.questions import MODES, Mode, QuestionSchema, Screen
from app.rules import RuleResult, suggest

Source = Literal["health_confirmed", "health_changed", "member"]


class SessionNotFound(LookupError):
    pass


class SessionConflict(ValueError):
    pass


class AnswerOut(BaseModel):
    value: Any
    source: Source


class RunStats(BaseModel):
    """What this run asked of the member, for the finish screen's comparison."""

    screens_seen: int
    filled_from_health: int
    changed_from_health: int
    estimates_taken: int


class SessionState(BaseModel):
    """Everything the web app needs to render or resume a session."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    member_id: MemberId
    mode: Mode
    next_screen_id: str | None
    answers: dict[str, AnswerOut]
    suggestions: dict[str, RuleResult]
    review_rows: list[str]
    health_summary: HealthSummaryV1 | None
    tap_count: int
    stats: RunStats
    finished: bool


def _member_id(session: IntakeSession) -> MemberId:
    if session.member_id not in MEMBER_IDS:
        raise ValueError(f"unknown member {session.member_id}")
    return session.member_id


def _mode(session: IntakeSession) -> Mode:
    if session.mode not in MODES:
        raise ValueError(f"unknown mode {session.mode}")
    return session.mode


def purge_expired(db: Session, now: datetime, ttl_hours: int) -> None:
    db.execute(delete(IntakeSession).where(IntakeSession.created_at < now - timedelta(hours=ttl_hours)))


def create_session(
    db: Session, member_id: MemberId, mode: Mode, client_key: str, now: datetime, settings: Settings
) -> IntakeSession:
    """Idempotent on `client_key`: a retried create returns the same session."""
    existing = db.scalar(select(IntakeSession).where(IntakeSession.client_key == client_key))
    if existing is not None:
        if (existing.member_id, existing.mode) != (member_id, mode):
            raise SessionConflict("client_key already used for a different session")
        return existing
    purge_expired(db, now, settings.session_ttl_hours)
    session = IntakeSession(client_key=client_key, member_id=member_id, mode=mode, created_at=now, tap_count=0)
    db.add(session)
    db.commit()
    return session


def get_session(db: Session, session_id: uuid.UUID, now: datetime, settings: Settings) -> IntakeSession:
    session = db.get(IntakeSession, session_id)
    if session is None or session.created_at < now - timedelta(hours=settings.session_ttl_hours):
        raise SessionNotFound(str(session_id))
    return session


def store_health_summary(db: Session, session: IntakeSession, summary: HealthSummaryV1, now: datetime) -> None:
    """The iPhone contract: store a HealthSummaryV1 for this session (replacing any earlier one)."""
    row = db.get(HealthSummaryRow, session.id)
    data = summary.model_dump(mode="json")
    if row is None:
        db.add(
            HealthSummaryRow(
                session_id=session.id,
                schema_version=summary.schema_version,
                data=data,
                data_class="device",
                received_at=now,
            )
        )
    else:
        row.schema_version, row.data, row.received_at = summary.schema_version, data, now
    db.commit()


def connect_simulated_health(db: Session, session: IntakeSession, now: datetime) -> None:
    """Stands in for the iPhone: read the synthetic member's HealthKit data and send the summary."""
    member = load_member(_member_id(session))
    store_health_summary(db, session, build_summary(resolve(member, now), now), now)


def _summary(db: Session, session: IntakeSession) -> HealthSummaryV1 | None:
    """Only Health first uses the summary; today's flow asks everything."""
    if session.mode != "health_first":
        return None
    row = db.get(HealthSummaryRow, session.id)
    return None if row is None else HealthSummaryV1.model_validate(row.data)


def _suggestions(
    db: Session, session: IntakeSession, schema: QuestionSchema, now: datetime, settings: Settings
) -> dict[str, RuleResult]:
    summary = _summary(db, session)
    return {} if summary is None else suggest(schema, summary, now, settings.rules)


def _review_rows(schema: QuestionSchema, suggestions: dict[str, RuleResult]) -> list[str]:
    review = next((s for s in schema.for_mode("health_first") if s.kind == "health_review"), None)
    if review is None:
        return []
    return [row for row in review.review_rows if row in suggestions and suggestions[row].status != "ask"]


def _source(value: Any, suggestion: RuleResult | None) -> Source:
    """Where an answer came from. "Changed" means the member edited a fact Health filled in; an estimate is only a
    hint, so picking something else is simply the member's own answer."""
    if suggestion is None or suggestion.status == "ask" or value is None:
        return "member"
    if value == suggestion.value:
        return "health_confirmed"
    return "health_changed" if suggestion.kind == "fact" else "member"


def _answers(db: Session, session: IntakeSession) -> dict[str, IntakeAnswer]:
    rows = db.scalars(select(IntakeAnswer).where(IntakeAnswer.session_id == session.id))
    return {row.screen_id: row for row in rows}


def _stats(answers: dict[str, IntakeAnswer], schema: QuestionSchema) -> RunStats:
    kinds = {s.id: s.health.kind for s in schema.screens if s.health is not None}
    review = answers.get("health_review")
    # Facts confirmed on the review card share its key; they were never separate screens.
    on_card = {
        k
        for k, row in answers.items()
        if review is not None and k in kinds and row.idempotency_key == review.idempotency_key
    }
    return RunStats(
        screens_seen=len(answers) - len(on_card),
        filled_from_health=sum(
            1 for k, r in answers.items() if kinds.get(k) == "fact" and r.source == "health_confirmed"
        ),
        changed_from_health=sum(1 for r in answers.values() if r.source == "health_changed"),
        estimates_taken=sum(
            1 for k, r in answers.items() if kinds.get(k) == "estimate" and r.source == "health_confirmed"
        ),
    )


def state(
    db: Session, session: IntakeSession, schema: QuestionSchema, now: datetime, settings: Settings
) -> SessionState:
    suggestions = _suggestions(db, session, schema, now, settings)
    review_rows = _review_rows(schema, suggestions)
    answers = _answers(db, session)
    next_screen = None
    for screen in schema.for_mode(_mode(session)):
        if screen.id in answers:
            continue
        if screen.kind == "health_review" and not review_rows:
            continue  # nothing to review (access denied, or no usable data)
        next_screen = screen.id
        break
    return SessionState(
        id=session.id,
        member_id=_member_id(session),
        mode=_mode(session),
        next_screen_id=next_screen,
        answers={k: AnswerOut(value=row.value, source=cast(Source, row.source)) for k, row in answers.items()},
        suggestions=suggestions,
        review_rows=review_rows,
        health_summary=_summary(db, session),
        tap_count=session.tap_count,
        stats=_stats(answers, schema),
        finished=next_screen is None,
    )


def _upsert(
    db: Session,
    session: IntakeSession,
    screen_id: str,
    value: Any,
    source: Source,
    suggestion: RuleResult | None,
    key: str,
    now: datetime,
    existing: dict[str, IntakeAnswer],
) -> None:
    payload = suggestion.model_dump(mode="json") if suggestion is not None else None
    row = existing.get(screen_id)
    if row is None:
        db.add(
            IntakeAnswer(
                session_id=session.id,
                screen_id=screen_id,
                value=value,
                source=source,
                suggestion=payload,
                idempotency_key=key,
                created_at=now,
                updated_at=now,
            )
        )
    else:
        row.value, row.source, row.suggestion, row.idempotency_key, row.updated_at = (
            value,
            source,
            payload,
            key,
            now,
        )


def submit_answer(
    db: Session,
    session: IntakeSession,
    screen: Screen,
    value: Any,
    idempotency_key: str,
    taps: int,
    schema: QuestionSchema,
    now: datetime,
    settings: Settings,
) -> None:
    """Save one answer. A retry with the same key changes nothing; a new key (after Back) replaces it."""
    if session.mode not in screen.modes:
        raise InvalidAnswer(f"{screen.id}: not part of this flow")
    existing = _answers(db, session)
    stored = existing.get(screen.id)
    if stored is not None and stored.idempotency_key == idempotency_key:
        return

    suggestions = _suggestions(db, session, schema, now, settings)
    if screen.kind == "health_review":
        rows = value.get("rows") if isinstance(value, dict) and set(value) == {"rows"} else None
        expected = _review_rows(schema, suggestions)
        if not isinstance(rows, dict) or set(rows) != set(expected):
            raise InvalidAnswer(f"{screen.id}: rows must be exactly {expected}")
        by_id = {s.id: s for s in schema.screens}
        for row_id in expected:
            validate(by_id[row_id], rows[row_id])
        for row_id in expected:
            suggestion = suggestions[row_id]
            _upsert(
                db,
                session,
                row_id,
                rows[row_id],
                _source(rows[row_id], suggestion),
                suggestion,
                idempotency_key,
                now,
                existing,
            )
        _upsert(db, session, screen.id, {"confirmed": True}, "member", None, idempotency_key, now, existing)
    else:
        validate(screen, value)
        hint = suggestions.get(screen.id)
        _upsert(
            db,
            session,
            screen.id,
            value,
            _source(value, hint),
            hint,
            idempotency_key,
            now,
            existing,
        )

    session.tap_count += max(0, taps)
    db.commit()

    if screen.kind == "health_permission" and session.mode == "health_first":
        if value == {"granted": True}:
            connect_simulated_health(db, session, now)
        else:  # access withdrawn (for example after Back): forget the Health data
            db.execute(delete(HealthSummaryRow).where(HealthSummaryRow.session_id == session.id))
            db.commit()
