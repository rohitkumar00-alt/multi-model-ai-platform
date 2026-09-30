from app.adapters.base import ModelAdapter
from app.adapters.mock import MockAdapter
from app.config import ModelConfig


def build_adapter(config: ModelConfig) -> ModelAdapter:
    """Pick the adapter class for a model's provider."""
    if config.provider == "mock":
        return MockAdapter(config)
    raise ValueError(f"Unknown provider '{config.provider}' for model '{config.id}'")
