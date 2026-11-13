"""Loads the committed synthetic member fixtures."""

from functools import lru_cache
from pathlib import Path

from app.health.models import MemberFixture, MemberId
from app.health.synthetic import MEMBERS_DIR

MEMBER_IDS: tuple[MemberId, ...] = ("a", "b", "c")


@lru_cache
def load_member(member_id: MemberId, members_dir: Path = MEMBERS_DIR) -> MemberFixture:
    return MemberFixture.model_validate_json((members_dir / f"{member_id}.json").read_text())
