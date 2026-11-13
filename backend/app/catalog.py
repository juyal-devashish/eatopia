"""The condition catalog the condition picker (and, from M6, Claude's matching) chooses from."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

CATALOG_PATH = Path(__file__).parent / "data" / "conditions.json"

Group = Literal["metabolic", "heart", "digestive", "kidney", "hormonal", "eating", "other"]


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    label: str
    group: Group


class ConditionCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    note: str
    conditions: tuple[Condition, ...]

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        ids = [condition.id for condition in self.conditions]
        if len(ids) != len(set(ids)):
            raise ValueError("condition ids must be unique")
        return self

    def ids(self) -> frozenset[str]:
        return frozenset(condition.id for condition in self.conditions)


@lru_cache
def load_catalog(path: Path = CATALOG_PATH) -> ConditionCatalog:
    return ConditionCatalog.model_validate_json(path.read_text())
