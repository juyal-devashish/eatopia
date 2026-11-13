"""FastAPI entry point for the intake API."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.answers import InvalidAnswer
from app.catalog import ConditionCatalog, load_catalog
from app.claude_client import (
    AnthropicTransport,
    CatalogRef,
    InvalidMemberText,
    MemberText,
    ModelTransport,
    build_match_request,
    call_model,
)
from app.clock import get_now
from app.config import Settings, get_settings
from app.db import IntakeSession, LlmCall, get_db
from app.egress import claim, finish, log_for
from app.health.members import MEMBER_IDS, load_member
from app.health.models import MemberId
from app.health.summary import HealthSummaryV1
from app.intake import (
    SessionConflict,
    SessionNotFound,
    SessionState,
    create_session,
    get_session,
    state,
    store_health_summary,
    submit_answer,
)
from app.questions import Mode, Screen, Section, load_schema

_transport: AnthropicTransport | None = None


def get_transport() -> ModelTransport:
    """The real Anthropic transport, created on first use. Tests replace it with a fake."""
    global _transport
    if _transport is None:
        settings = get_settings()
        _transport = AnthropicTransport(settings.llm, settings.anthropic_api_key)
    return _transport


Db = Annotated[Session, Depends(get_db)]
Now = Annotated[datetime, Depends(get_now)]
Config = Annotated[Settings, Depends(get_settings)]
Transport = Annotated[ModelTransport, Depends(get_transport)]
Key = Annotated[str, Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class FormResponse(BaseModel):
    version: int
    mode: Mode
    sections: tuple[Section, ...]
    screens: tuple[Screen, ...]


class MemberSummary(BaseModel):
    """What the start screen shows about a synthetic member. Labels only, never Health values."""

    id: MemberId
    label: str
    description: str


class CreateSession(BaseModel):
    member_id: MemberId
    mode: Mode
    client_key: Key


class AnswerIn(BaseModel):
    screen_id: str
    value: Any
    idempotency_key: Key
    taps: int = Field(default=0, ge=0, le=500)


class MatchIn(BaseModel):
    text: str = Field(max_length=2_000)
    request_key: Key


class MatchedCondition(BaseModel):
    condition_id: str
    label: str
    confidence: str


class MatchOut(BaseModel):
    """Suggestions for the member to tap. When matching can't help, the web app shows the full list."""

    call_id: int
    status: str
    matches: list[MatchedCondition]
    show_full_list: bool


class EgressEntry(BaseModel):
    """One model call as the "What the model saw" panel shows it. `request` is exactly what was sent."""

    id: int
    purpose: str
    status: str
    model: str
    request: dict[str, Any] | None
    result: dict[str, Any] | None
    error: str | None
    latency_ms: int | None
    created_at: datetime


def _match_out(row: LlmCall, catalog: CatalogRef) -> MatchOut:
    matches = [
        MatchedCondition(
            condition_id=m["condition_id"], label=catalog.label(m["condition_id"]), confidence=m["confidence"]
        )
        for m in (row.result or {}).get("matches", [])
    ]
    return MatchOut(
        call_id=row.id, status=row.status, matches=matches, show_full_list=row.status != "ok" or not matches
    )


def _load(db: Session, session_id: uuid.UUID, now: datetime, settings: Settings) -> IntakeSession:
    try:
        return get_session(db, session_id, now, settings)
    except SessionNotFound as error:
        raise HTTPException(status_code=404, detail="Session not found or expired") from error


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Health-first intake API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    @app.get("/form")
    def form(mode: Mode) -> FormResponse:
        schema = load_schema()
        return FormResponse(version=schema.version, mode=mode, sections=schema.sections, screens=schema.for_mode(mode))

    @app.get("/catalog/conditions")
    def conditions() -> ConditionCatalog:
        return load_catalog()

    @app.get("/members")
    def members() -> list[MemberSummary]:
        return [
            MemberSummary(id=m.id, label=m.label, description=m.description)
            for m in (load_member(member_id) for member_id in MEMBER_IDS)
        ]

    @app.post("/sessions")
    def new_session(body: CreateSession, db: Db, now: Now, config: Config) -> SessionState:
        try:
            session = create_session(db, body.member_id, body.mode, body.client_key, now, config)
        except SessionConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return state(db, session, load_schema(), now, config)

    @app.get("/sessions/{session_id}")
    def resume(session_id: uuid.UUID, db: Db, now: Now, config: Config) -> SessionState:
        return state(db, _load(db, session_id, now, config), load_schema(), now, config)

    @app.post("/sessions/{session_id}/answers")
    def answer(session_id: uuid.UUID, body: AnswerIn, db: Db, now: Now, config: Config) -> SessionState:
        session = _load(db, session_id, now, config)
        schema = load_schema()
        screen = next((s for s in schema.screens if s.id == body.screen_id), None)
        if screen is None:
            raise HTTPException(status_code=404, detail="Unknown screen")
        try:
            submit_answer(db, session, screen, body.value, body.idempotency_key, body.taps, schema, now, config)
        except InvalidAnswer as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return state(db, session, schema, now, config)

    @app.post("/sessions/{session_id}/health-summary")
    def health_summary(session_id: uuid.UUID, body: HealthSummaryV1, db: Db, now: Now, config: Config) -> SessionState:
        """The one request an iPhone app would make after reading HealthKit."""
        session = _load(db, session_id, now, config)
        store_health_summary(db, session, body, now)
        return state(db, session, load_schema(), now, config)

    @app.post("/sessions/{session_id}/conditions/match")
    async def match_condition(
        session_id: uuid.UUID, body: MatchIn, db: Db, now: Now, config: Config, transport: Transport
    ) -> MatchOut:
        """Suggest conditions for what the member typed. Only their text and the catalog are sent."""
        session = await run_in_threadpool(_load, db, session_id, now, config)
        try:
            text = MemberText.from_member(body.text, config.llm.max_member_chars)
        except InvalidMemberText as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        catalog = CatalogRef.from_catalog(load_catalog())
        request = build_match_request(text, catalog, config.llm)

        kind, row = await run_in_threadpool(
            claim, db, session, "condition_match", body.request_key, request, now, config.llm
        )
        if kind == "existing" and row.status == "pending":
            raise HTTPException(status_code=409, detail="Still matching; try again in a moment")
        if kind == "claimed":
            outcome = await call_model(transport, request, catalog, config.llm)
            row = await run_in_threadpool(finish, db, row.id, outcome, now)
        return _match_out(row, catalog)

    @app.get("/sessions/{session_id}/egress")
    def egress(session_id: uuid.UUID, db: Db, now: Now, config: Config) -> list[EgressEntry]:
        session = _load(db, session_id, now, config)
        return [EgressEntry.model_validate(row, from_attributes=True) for row in log_for(db, session)]

    return app


app = create_app()
