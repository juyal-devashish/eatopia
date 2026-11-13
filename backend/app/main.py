"""FastAPI entry point for the intake API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.catalog import ConditionCatalog, load_catalog
from app.config import get_settings
from app.health.members import MEMBER_IDS, load_member
from app.health.models import MemberId
from app.questions import Mode, Screen, Section, load_schema


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
        return FormResponse(
            version=schema.version,
            mode=mode,
            sections=schema.sections,
            screens=schema.for_mode(mode),
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

    return app


app = create_app()
