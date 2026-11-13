"""FastAPI entry point for the intake API."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.answers import InvalidAnswer, validate
from app.baseline import Baseline, one_per_screen
from app.catalog import ConditionCatalog, load_catalog
from app.claude_client import (
    AnthropicTransport,
    CatalogRef,
    InvalidMemberText,
    MemberText,
    ModelTransport,
    VoiceQuestion,
    VoiceQuestions,
    build_extract_request,
    build_match_request,
    build_option_request,
    build_summary_request,
    call_model,
    parse_extract,
    parse_summary,
)
from app.clock import get_now
from app.config import Settings, get_settings
from app.db import IntakeSession, LlmCall, get_db
from app.dietitian import fill_placeholders, member_answers, placeholders, template_summary
from app.egress import claim, finish, log_for
from app.health.members import MEMBER_IDS, load_member
from app.health.models import MemberId
from app.health.summary import HealthSummaryV1
from app.intake import (
    VOICE_PURPOSE,
    SessionConflict,
    SessionNotFound,
    SessionState,
    create_session,
    get_session,
    session_exists,
    state,
    store_health_summary,
    submit_answer,
)
from app.offline_model import OFFLINE_MODEL, OfflineTransport
from app.questions import Mode, Screen, Section, load_schema
from app.ratelimit import SessionLimiter, client_address

_transport: ModelTransport | None = None


def get_transport() -> ModelTransport:
    """The Anthropic transport, created on first use. `LLM_TRANSPORT=offline` swaps in a keyword matcher for
    end-to-end runs and keyless local use; unit tests replace it with a fake."""
    global _transport
    if _transport is None:
        settings = get_settings()
        if settings.llm_transport == "offline":
            _transport = OfflineTransport()
        else:
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
    baseline: Baseline  # the same questions asked one per screen, for comparison


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
    text: str = Field(max_length=4_000)
    request_key: Key


class MatchedItem(BaseModel):
    id: str
    label: str
    confidence: str


class MatchOut(BaseModel):
    """Suggestions for the member to tap. When matching can't help, the web app shows the full list."""

    call_id: int
    status: str
    matches: list[MatchedItem]
    show_full_list: bool


class SummaryIn(BaseModel):
    request_key: Key


class SummaryOut(BaseModel):
    """The dietitian summary with Health values filled in by code, or a plain fallback when it couldn't be written."""

    call_id: int
    status: str
    text: str
    written_by_model: bool
    writer: str | None  # the model that answered, or the offline stand-in
    health_values_filled: list[str]


class ExtractOut(BaseModel):
    """What the member said, turned into answers for them to confirm. `null` means not mentioned: the web app
    asks that question on the same screen. When extraction fails, every answer is null."""

    call_id: int
    status: str
    answers: dict[str, Any]


def voice_questions(screen: Screen, screens: dict[str, Screen]) -> VoiceQuestions:
    """The covered questions as the model may see them: wording and option ids from our schema only."""
    items = []
    for covered_id in screen.covers:
        q = screens[covered_id]
        options = tuple((o.id, o.label) for o in q.options if not o.free_text)
        items.append(VoiceQuestion(id=q.id, kind=q.kind, title=q.title, options=options))  # type: ignore[arg-type]
    return VoiceQuestions(items=tuple(items))


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


def checked_answers(
    raw: dict[str, Any], screen: Screen, screens: dict[str, Screen], said: MemberText
) -> dict[str, Any]:
    """Drop anything that isn't a valid answer, and any "own words" the member didn't actually say."""
    answers: dict[str, Any] = {}
    for covered_id in screen.covers:
        value = raw.get(covered_id)
        if value is not None and screens[covered_id].kind == "text" and _normalise(value) not in _normalise(said.text):
            value = None
        if value is not None:
            try:
                validate(screens[covered_id], value)
            except InvalidAnswer:
                value = None
        answers[covered_id] = value
    return answers


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
        MatchedItem(id=m["id"], label=catalog.label(m["id"]), confidence=m["confidence"])
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
    limiter = SessionLimiter(settings.sessions_per_hour_per_client)
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
        return FormResponse(
            version=schema.version,
            mode=mode,
            sections=schema.sections,
            screens=schema.for_mode(mode),
            baseline=one_per_screen(schema),
        )

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
    def new_session(body: CreateSession, request: Request, db: Db, now: Now, config: Config) -> SessionState:
        # A retried create (same client key) is never limited; only new sessions count.
        if not session_exists(db, body.client_key) and not limiter.allow(client_address(request), now):
            raise HTTPException(status_code=429, detail="Too many new sessions from here. Try again in an hour.")
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

    async def run_match(
        db: Session,
        session: IntakeSession,
        purpose: str,
        key: str,
        request: dict[str, Any],
        choices: CatalogRef,
        now: datetime,
        config: Settings,
        transport: ModelTransport,
    ) -> MatchOut:
        """Claim the call (a retry returns the stored result), send it unless capped, and log the outcome."""
        kind, row = await run_in_threadpool(claim, db, session, purpose, key, request, now, config.llm)
        if kind == "existing" and row.status == "pending":
            raise HTTPException(status_code=409, detail="Still matching; try again in a moment")
        if kind == "claimed":
            outcome = await call_model(transport, request, choices, config.llm)
            row = await run_in_threadpool(finish, db, row.id, outcome, now)
        return _match_out(row, choices)

    def member_text(raw: str, config: Settings) -> MemberText:
        try:
            return MemberText.from_member(raw, config.llm.max_member_chars)
        except InvalidMemberText as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/sessions/{session_id}/conditions/match")
    async def match_condition(
        session_id: uuid.UUID, body: MatchIn, db: Db, now: Now, config: Config, transport: Transport
    ) -> MatchOut:
        """Suggest conditions for what the member typed. Only their text and the catalog are sent."""
        session = await run_in_threadpool(_load, db, session_id, now, config)
        text = member_text(body.text, config)
        catalog = CatalogRef.from_catalog(load_catalog())
        request = build_match_request(text, catalog, config.llm)
        return await run_match(
            db, session, "condition_match", body.request_key, request, catalog, now, config, transport
        )

    @app.post("/sessions/{session_id}/screens/{screen_id}/match")
    async def match_option(
        session_id: uuid.UUID,
        screen_id: str,
        body: MatchIn,
        db: Db,
        now: Now,
        config: Config,
        transport: Transport,
    ) -> MatchOut:
        """Map a "Something else" answer onto the question's own options, for the member to tap or ignore."""
        session = await run_in_threadpool(_load, db, session_id, now, config)
        screen = next((s for s in load_schema().screens if s.id == screen_id), None)
        if screen is None or not any(o.free_text for o in screen.options):
            raise HTTPException(status_code=404, detail="That question has no free-text option")
        text = member_text(body.text, config)
        options = CatalogRef(items=tuple((o.id, o.label) for o in screen.options if not o.free_text))
        request = build_option_request(text, screen.title, options, config.llm)
        return await run_match(db, session, "option_match", body.request_key, request, options, now, config, transport)

    @app.post("/sessions/{session_id}/screens/{screen_id}/extract")
    async def extract(
        session_id: uuid.UUID,
        screen_id: str,
        body: MatchIn,
        db: Db,
        now: Now,
        config: Config,
        transport: Transport,
    ) -> ExtractOut:
        """Fill a voice screen's questions from what the member said. The iPhone app would send its on-device
        transcript here; the web demo sends a simulated one. Only the text and our own lists reach the model."""
        session = await run_in_threadpool(_load, db, session_id, now, config)
        schema = load_schema()
        screens = {s.id: s for s in schema.screens}
        screen = screens.get(screen_id)
        if screen is None or screen.kind != "voice" or session.mode not in screen.modes:
            raise HTTPException(status_code=404, detail="That screen doesn't take a spoken answer")
        try:
            said = MemberText.from_member(body.text, config.llm.max_voice_chars)
        except InvalidMemberText as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        questions = voice_questions(screen, screens)
        catalog = CatalogRef.from_catalog(load_catalog())
        request = build_extract_request(said, questions, catalog, config.llm)

        def parse(response: dict[str, Any]) -> dict[str, Any]:
            answers = checked_answers(parse_extract(response, questions, catalog), screen, screens, said)
            return {"screen_id": screen_id, "answers": answers}

        kind, row = await run_in_threadpool(
            claim, db, session, VOICE_PURPOSE, body.request_key, request, now, config.llm
        )
        if kind == "existing" and row.status == "pending":
            raise HTTPException(status_code=409, detail="Still listening; try again in a moment")
        if kind == "claimed":
            outcome = await call_model(transport, request, parse, config.llm)
            row = await run_in_threadpool(finish, db, row.id, outcome, now)
        answers = (row.result or {}).get("answers") if row.status == "ok" else None
        return ExtractOut(call_id=row.id, status=row.status, answers=answers or {c: None for c in screen.covers})

    @app.post("/sessions/{session_id}/summary")
    async def summary(
        session_id: uuid.UUID, body: SummaryIn, db: Db, now: Now, config: Config, transport: Transport
    ) -> SummaryOut:
        """A short note for the dietitian. The model sees the member's own answers, never a Health value."""
        session = await run_in_threadpool(_load, db, session_id, now, config)
        schema, catalog = load_schema(), load_catalog()
        current = await run_in_threadpool(state, db, session, schema, now, config)
        answers = {k: a.value for k, a in current.answers.items()}
        request = build_summary_request(member_answers(schema, answers, catalog), placeholders(schema), config.llm)

        kind, row = await run_in_threadpool(
            claim, db, session, "dietitian_summary", body.request_key, request, now, config.llm
        )
        if kind == "existing" and row.status == "pending":
            raise HTTPException(status_code=409, detail="Still writing; try again in a moment")
        if kind == "claimed":
            outcome = await call_model(transport, request, parse_summary, config.llm)
            row = await run_in_threadpool(finish, db, row.id, outcome, now)
        writer = (row.response or {}).get("model")
        if row.status != "ok" or not row.result:
            return SummaryOut(
                call_id=row.id,
                status=row.status,
                text=template_summary(row.status),
                written_by_model=False,
                writer=writer,
                health_values_filled=[],
            )
        text, filled = fill_placeholders(str(row.result["summary"]), schema, answers, catalog)
        return SummaryOut(
            call_id=row.id,
            status=row.status,
            text=text,
            written_by_model=writer != OFFLINE_MODEL,
            writer=writer,
            health_values_filled=filled,
        )

    @app.get("/sessions/{session_id}/egress")
    def egress(session_id: uuid.UUID, db: Db, now: Now, config: Config) -> list[EgressEntry]:
        session = _load(db, session_id, now, config)
        return [EgressEntry.model_validate(row, from_attributes=True) for row in log_for(db, session)]

    return app


app = create_app()
