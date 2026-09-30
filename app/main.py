"""FastAPI app: the only place that talks to model providers, and the
server that hosts the frontend page."""
import asyncio
import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.adapters import build_adapter
from app.config import load_settings
from app.coordinator import build_coordinator
from app.orchestrator import fan_out
from app.schemas import (
    Analysis,
    AskRequest,
    AskResponse,
    CoordinatorResult,
    ModelInfo,
    ModelStatus,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("api")

settings = load_settings()  # fails fast with a clear error if models.yaml is bad
adapters = {cfg.id: build_adapter(cfg) for cfg in settings.models}
coordinator_adapter = build_coordinator(settings.coordinator)

FRONTEND_FILE = Path(__file__).resolve().parent.parent / "static" / "index.html"

app = FastAPI(title="Multi-Model Answer Platform", version="0.2.0")


@app.get("/", include_in_schema=False)
async def frontend():
    return FileResponse(FRONTEND_FILE)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/models", response_model=list[ModelInfo])
async def list_models():
    return [ModelInfo(**cfg.model_dump(include=set(ModelInfo.model_fields))) for cfg in settings.models]


async def run_coordinator(question: str, results, timeout: float) -> CoordinatorResult:
    """Never lets a coordinator failure break the whole request."""
    try:
        return await asyncio.wait_for(coordinator_adapter.synthesize(question, results), timeout=timeout)
    except asyncio.TimeoutError:
        return CoordinatorResult(
            final_answer="The coordinator did not finish in time, so no combined answer is available this time.",
            uncertainty_note="Coordinator step timed out; the individual model answers above are still valid.",
            analysis=Analysis(),
            skipped_reason="coordinator_timeout",
        )
    except Exception:
        logger.exception("Coordinator step failed")
        return CoordinatorResult(
            final_answer="The coordinator could not synthesize a combined answer this time.",
            uncertainty_note="Coordinator step failed; the individual model answers above are still valid.",
            analysis=Analysis(),
            skipped_reason="coordinator_error",
        )


@app.post("/api/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    unknown = [m for m in req.model_ids if m not in adapters]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown model ids: {', '.join(unknown)}")

    timeout = req.timeout_seconds or settings.default_timeout_seconds
    request_id = uuid.uuid4().hex[:12]
    start = time.perf_counter()

    results = await fan_out(req.question, [adapters[m] for m in req.model_ids], timeout)
    coordinator_result = await run_coordinator(req.question, results, timeout)

    succeeded = sum(1 for r in results if r.status == ModelStatus.OK)
    total_ms = int((time.perf_counter() - start) * 1000)
    logger.info("request=%s models=%d ok=%d total_ms=%d", request_id, len(results), succeeded, total_ms)

    return AskResponse(
        request_id=request_id,
        question=req.question,
        results=results,
        succeeded=succeeded,
        failed=len(results) - succeeded,
        total_latency_ms=total_ms,
        coordinator=coordinator_result,
    )
