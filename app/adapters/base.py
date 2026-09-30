"""The one interface every model provider must implement."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.config import ModelConfig


class ModelCallError(Exception):
    """A provider call failed in an expected way. The message is safe to show users."""


@dataclass
class Generation:
    text: str
    tokens_in: int | None = None
    tokens_out: int | None = None


class ModelAdapter(ABC):
    def __init__(self, config: ModelConfig):
        self.config = config

    @abstractmethod
    async def generate(self, prompt: str) -> Generation:
        """Return the model's answer or raise ModelCallError."""
