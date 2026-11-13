"""Settings read from the environment. Names are listed in backend/.env.example."""

from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuleSettings(BaseModel):
    """Thresholds for the Health mapping rules. Changing one changes answers, so tests pin them."""

    weight_fresh_days: int = 30
    weight_max_age_days: int = 90
    steps_min_days: int = 14
    activity_light_from: int = 5_000
    activity_moderate_from: int = 7_500
    activity_very_from: int = 10_000
    min_age: int = 13
    max_age: int = 110
    min_height_cm: float = 100
    max_height_cm: float = 250
    min_weight_kg: float = 30
    max_weight_kg: float = 300


class LlmSettings(BaseModel):
    """Model, limits and caps for every Claude call. The public demo link spends real money, so caps are low."""

    model: str = "claude-opus-5-5"
    timeout_seconds: float = 30
    max_retries: int = 1
    session_cap: int = 5
    daily_cap: int = 300
    match_effort: str = "low"
    match_max_tokens: int = 4_000
    max_member_chars: int = 300
    refusal_fallback: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    allowed_origins: list[str] = ["http://localhost:3000"]
    database_url: str = "postgresql+psycopg:///intake"
    session_ttl_hours: int = 24
    rules: RuleSettings = RuleSettings()
    llm: LlmSettings = LlmSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
