"""Database engine, session and table definitions (SQLAlchemy 2)."""

import uuid
from collections.abc import Iterator
from datetime import datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    type_annotation_map = {datetime: DateTime(timezone=True), dict[str, Any]: JSONB}


class IntakeSession(Base):
    __tablename__ = "intake_session"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_key: Mapped[str] = mapped_column(String(64), unique=True)
    member_id: Mapped[str] = mapped_column(String(8))
    mode: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]
    tap_count: Mapped[int] = mapped_column(default=0)


class HealthSummaryRow(Base):
    """The stored HealthSummaryV1. Device data: rules and member only, never the model."""

    __tablename__ = "health_summary"
    __table_args__ = (CheckConstraint("data_class = 'device'", name="health_summary_is_device_data"),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intake_session.id", ondelete="CASCADE"), primary_key=True
    )
    schema_version: Mapped[int]
    data: Mapped[dict[str, Any]]
    data_class: Mapped[str] = mapped_column(String(16), default="device")
    received_at: Mapped[datetime]


class IntakeAnswer(Base):
    """One answer per session and screen. `suggestion` keeps the rule result the member saw."""

    __tablename__ = "intake_answer"
    __table_args__ = (UniqueConstraint("session_id", "screen_id", name="one_answer_per_screen"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intake_session.id", ondelete="CASCADE"))
    screen_id: Mapped[str] = mapped_column(String(64))
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)  # SQL NULL means skipped
    source: Mapped[str] = mapped_column(String(24))
    suggestion: Mapped[dict[str, Any] | None]
    idempotency_key: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


@lru_cache
def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or get_settings().database_url, pool_pre_ping=True)


def get_db() -> Iterator[Session]:
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    with factory() as db:
        yield db
