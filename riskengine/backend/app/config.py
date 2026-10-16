"""Central configuration. All tunables live here or in .env — no magic numbers in logic."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_name: str = "AI/NLP Financial Risk Engine"
    version: str = "0.1.0"
    log_level: str = "INFO"

    newsapi_key: str = ""
    alphavantage_key: str = ""
    use_live_data: bool = False
    sentiment_backend: Literal["finbert", "lexicon"] = "finbert"

    gdelt_query: str = "(earnings OR bankruptcy OR sanctions OR merger OR recall OR \"interest rate\") sourcelang:english"
    ingest_limit: int = 500
    http_timeout: float = 8.0

    stress_trigger_impact: float = Field(7.0, ge=1.0, le=10.0)
    # Upper bounds (exclusive) of each risk band on the 1-10 impact scale.
    # Tuned against the impact-score distribution in Phase 4; defaults are provisional.
    risk_bands: dict[str, float] = {"LOW": 3.0, "MEDIUM": 6.0, "HIGH": 8.0, "CRITICAL": 10.01}

    data_dir: Path = ROOT / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
