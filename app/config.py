"""Loads and validates models.yaml."""
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "models.yaml"


class MockSettings(BaseModel):
    min_delay: float = Field(0.3, ge=0)
    max_delay: float = Field(1.5, ge=0)
    error_rate: float = Field(0.0, ge=0, le=1)

    @model_validator(mode="after")
    def check_range(self):
        if self.max_delay < self.min_delay:
            raise ValueError("max_delay must be >= min_delay")
        return self
class HttpSettings(BaseModel):
    api_key_env: str
    model: str
    endpoint: str | None = None    


class ModelConfig(BaseModel):
    id: str
    label: str
    provider: str
    price_per_1k_input_usd: float = Field(0.0, ge=0)
    price_per_1k_output_usd: float = Field(0.0, ge=0)
    mock: MockSettings = Field(default_factory=MockSettings)
    http: HttpSettings | None = None


class Settings(BaseModel):
    default_timeout_seconds: float = Field(30.0, gt=0, le=120)
    models: list[ModelConfig]
    coordinator: ModelConfig

    @model_validator(mode="after")
    def check_unique_ids(self):
        ids = [m.id for m in self.models]
        if len(ids) != len(set(ids)):
            raise ValueError("models.yaml contains duplicate model ids")
        return self


def load_settings(path: str | Path | None = None) -> Settings:
    """Read the YAML file (path arg > MODELS_CONFIG env var > default)."""
    config_path = Path(path or os.environ.get("MODELS_CONFIG") or DEFAULT_CONFIG_PATH)
    if not config_path.exists():
        raise RuntimeError(f"Model config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return Settings(**raw)
