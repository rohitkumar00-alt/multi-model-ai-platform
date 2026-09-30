"""A fake model for building and testing without API keys."""
import asyncio
import random

from app.adapters.base import Generation, ModelAdapter, ModelCallError
from app.stance import stance_for


class MockAdapter(ModelAdapter):
    async def generate(self, prompt: str) -> Generation:
        settings = self.config.mock
        await asyncio.sleep(random.uniform(settings.min_delay, settings.max_delay))

        if random.random() < settings.error_rate:
            raise ModelCallError("Simulated provider error (HTTP 503)")

        preview = prompt if len(prompt) <= 120 else prompt[:117] + "..."
        flavor = {
            "confident": "It states the answer plainly and with confidence.",
            "cautious": "It hedges and suggests double-checking an authoritative source.",
            "detailed": "It adds extra background detail beyond the core answer.",
        }[stance_for(self.config.id)]
        text = (
            f"[{self.config.label}] This is a mock answer, not real model output. "
            f"You asked: \"{preview}\" {flavor}"
        )
        return Generation(
            text=text,
            tokens_in=max(1, len(prompt) // 4),
            tokens_out=max(1, len(text) // 4),
        )
