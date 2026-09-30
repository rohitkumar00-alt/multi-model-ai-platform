import asyncio

from app.config import ModelConfig
from app.coordinator import MockCoordinatorAdapter
from app.schemas import ModelResult, ModelStatus

coordinator = MockCoordinatorAdapter(ModelConfig(id="c", label="C", provider="mock"))


def synth(results):
    return asyncio.run(coordinator.synthesize("q", results))


def ok(model_id, text="answer"):
    return ModelResult(model_id=model_id, label=model_id, status=ModelStatus.OK, text=text, latency_ms=10)


def failed(model_id, status=ModelStatus.ERROR):
    return ModelResult(model_id=model_id, label=model_id, status=status, latency_ms=10, error_message="x")


def test_no_successes_is_flagged_clearly():
    result = synth([failed("a"), failed("b", ModelStatus.TIMEOUT)])
    assert result.skipped_reason == "no_successful_responses"
    assert result.uncertainty_note


def test_single_success_notes_no_crosscheck():
    result = synth([ok("a"), failed("b")])
    assert result.final_answer == "answer"
    assert "only one model" in result.uncertainty_note.lower()


def test_multiple_successes_produce_supported_by_mapping():
    result = synth([ok("a"), ok("b"), ok("c")])
    all_ids = [mid for group in result.supported_by.values() for mid in group]
    assert sorted(all_ids) == ["a", "b", "c"]


def test_partial_failure_is_mentioned_in_uncertainty():
    result = synth([ok("a"), ok("b"), failed("c")])
    assert "c" in result.uncertainty_note
