from app.adapters.base import ModelAdapter
from app.adapters.mock import MockAdapter
from app.adapters.http_adapter import GeminiAdapter, OpenAICompatibleAdapter
from app.config import ModelConfig


def build_adapter(config: ModelConfig) -> ModelAdapter:
    """Pick the adapter class for a model's provider."""
    if config.provider == "mock":
        return MockAdapter(config)
    if config.provider in ("groq", "openrouter"):
        return OpenAICompatibleAdapter(config)
    if config.provider == "gemini":
        return GeminiAdapter(config)
    raise ValueError(f"Unknown provider '{config.provider}' for model '{config.id}'")