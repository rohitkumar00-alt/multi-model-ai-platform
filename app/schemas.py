"""Request and response shapes for the API."""
from enum import Enum

from pydantic import BaseModel, Field, field_validator

MAX_QUESTION_CHARS = 4000
MIN_MODELS = 2
MAX_MODELS = 6


class ModelStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


class AskRequest(BaseModel):
    question: str
    model_ids: list[str] = Field(min_length=MIN_MODELS, max_length=MAX_MODELS)
    timeout_seconds: float | None = Field(default=None, gt=0, le=120)

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be empty")
        if len(v) > MAX_QUESTION_CHARS:
            raise ValueError(f"question must be at most {MAX_QUESTION_CHARS} characters")
        return v

    @field_validator("model_ids")
    @classmethod
    def validate_model_ids(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("model_ids must not contain duplicates")
        return v


class ModelResult(BaseModel):
    """One model's outcome. Always returned, even on failure."""
    model_id: str
    label: str
    status: ModelStatus
    text: str | None = None
    latency_ms: int
    tokens_in: int | None = None
    tokens_out: int | None = None
    est_cost_usd: float | None = None  # an estimate, not a bill
    error_message: str | None = None


class Analysis(BaseModel):
    """Plain-language notes on where responses lined up or split."""
    agreements: list[str] = Field(default_factory=list)
    disagreements: list[str] = Field(default_factory=list)


class CoordinatorResult(BaseModel):
    """
    The coordinator's synthesis. It can compare and combine the responses it
    was given - it CANNOT verify they are correct, and it may itself make
    mistakes. Treat this as a helpful summary, not a guaranteed answer.
    """
    final_answer: str
    uncertainty_note: str | None = None
    analysis: Analysis
    supported_by: dict[str, list[str]] = Field(default_factory=dict)  # group label -> model_ids
    skipped_reason: str | None = None  # set when synthesis was skipped or failed


class AskResponse(BaseModel):
    request_id: str
    question: str
    results: list[ModelResult]
    succeeded: int
    failed: int
    total_latency_ms: int
    coordinator: CoordinatorResult


class ModelInfo(BaseModel):
    id: str
    label: str
    provider: str
    price_per_1k_input_usd: float
    price_per_1k_output_usd: float
