"""Runs several models at the same time and collects every outcome."""
import asyncio
import logging
import time

from app.adapters.base import ModelAdapter, ModelCallError
from app.schemas import ModelResult, ModelStatus

logger = logging.getLogger("orchestrator")


def estimate_cost(adapter: ModelAdapter, tokens_in: int | None, tokens_out: int | None) -> float | None:
    if tokens_in is None or tokens_out is None:
        return None
    cfg = adapter.config
    cost = (tokens_in / 1000) * cfg.price_per_1k_input_usd + (tokens_out / 1000) * cfg.price_per_1k_output_usd
    return round(cost, 6)


async def call_model(adapter: ModelAdapter, prompt: str, timeout: float) -> ModelResult:
    """Call one model. Never raises: every failure becomes a ModelResult."""
    cfg = adapter.config
    start = time.perf_counter()

    def elapsed_ms() -> int:
        return int((time.perf_counter() - start) * 1000)

    try:
        gen = await asyncio.wait_for(adapter.generate(prompt), timeout=timeout)
    except asyncio.TimeoutError:
        return ModelResult(
            model_id=cfg.id, label=cfg.label, status=ModelStatus.TIMEOUT,
            latency_ms=elapsed_ms(), error_message=f"No response within {timeout:g}s",
        )
    except ModelCallError as exc:
        return ModelResult(
            model_id=cfg.id, label=cfg.label, status=ModelStatus.ERROR,
            latency_ms=elapsed_ms(), error_message=str(exc),
        )
    except Exception:
        # Unknown bug: log details server-side, show only a generic message.
        logger.exception("Unexpected error from model %s", cfg.id)
        return ModelResult(
            model_id=cfg.id, label=cfg.label, status=ModelStatus.ERROR,
            latency_ms=elapsed_ms(), error_message="Unexpected error while calling this model",
        )

    return ModelResult(
        model_id=cfg.id, label=cfg.label, status=ModelStatus.OK, text=gen.text,
        latency_ms=elapsed_ms(), tokens_in=gen.tokens_in, tokens_out=gen.tokens_out,
        est_cost_usd=estimate_cost(adapter, gen.tokens_in, gen.tokens_out),
    )


async def fan_out(prompt: str, adapters: list[ModelAdapter], timeout: float) -> list[ModelResult]:
    """Send the prompt to every adapter concurrently; results keep the input order."""
    return list(await asyncio.gather(*(call_model(a, prompt, timeout) for a in adapters)))
