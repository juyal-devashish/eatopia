"""Simulated dictation: what each synthetic member says on the voice screens.

The real app would transcribe speech on the iPhone and send only the text. The web demo plays these scripts into
the transcript box instead. They are member-entered text, never Health data.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.health.models import MemberId

VOICE_DIR = Path(__file__).parent / "data" / "voice"


class VoiceScripts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    synthetic: bool
    note: str
    scripts: dict[str, str]


@lru_cache
def load_scripts(member_id: MemberId) -> dict[str, str]:
    """Scripts by voice screen id. Members without a file have none; the visitor types instead."""
    path = VOICE_DIR / f"{member_id}.json"
    if not path.exists():
        return {}
    data = VoiceScripts.model_validate_json(path.read_text())
    if not data.synthetic:
        raise ValueError(f"{path.name}: voice scripts must be synthetic")
    return data.scripts
