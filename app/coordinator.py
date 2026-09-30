"""
Combines the panel's answers into one response. Swappable like the model
adapters: add a real (LLM-backed) CoordinatorAdapter later without touching
main.py.

IMPORTANT: a coordinator - mock or real - can compare and merge answers,
but it cannot verify they are true, and it can itself be wrong (it may
share a blind spot with the panel, misread a disagreement as agreement,
or hallucinate its own synthesis). Never present its output as verified.
"""
from abc import ABC, abstractmethod

from app.config import ModelConfig
from app.schemas import Analysis, CoordinatorResult, ModelResult, ModelStatus
from app.stance import stance_for


class CoordinatorAdapter(ABC):
    def __init__(self, config: ModelConfig):
        self.config = config

    @abstractmethod
    async def synthesize(self, question: str, results: list[ModelResult]) -> CoordinatorResult:
        """Combine results into one CoordinatorResult. Should not raise;
        callers add a fallback, but a well-behaved adapter reports its own
        failures as a skipped_reason instead of throwing."""


class MockCoordinatorAdapter(CoordinatorAdapter):
    """
    Rule-based stand-in for a real coordinator. It does NOT read or
    understand the answers - it groups models by a fixed per-model label
    (see app/stance.py) purely to demonstrate the response shape
    (agreements / disagreements / a combined answer / an uncertainty
    note) that a real, meaning-aware coordinator will fill in for real.
    """

    async def synthesize(self, question: str, results: list[ModelResult]) -> CoordinatorResult:
        ok = [r for r in results if r.status == ModelStatus.OK]
        failed = [r for r in results if r.status != ModelStatus.OK]

        if not ok:
            return CoordinatorResult(
                final_answer="No model returned a usable answer, so there is nothing to combine.",
                uncertainty_note="Every selected model failed or timed out.",
                analysis=Analysis(),
                skipped_reason="no_successful_responses",
            )

        if len(ok) == 1:
            only = ok[0]
            note = "Only one model responded successfully, so there is nothing to cross-check it against."
            if failed:
                note += f" ({len(failed)} model(s) did not respond: {', '.join(r.label for r in failed)}.)"
            return CoordinatorResult(
                final_answer=only.text or "",
                uncertainty_note=note,
                analysis=Analysis(),
                supported_by={"only_response": [only.model_id]},
            )

        groups: dict[str, list[ModelResult]] = {}
        for r in ok:
            groups.setdefault(stance_for(r.model_id), []).append(r)

        majority_label = max(groups, key=lambda s: len(groups[s]))
        majority_group = groups[majority_label]

        agreements = []
        if len(majority_group) > 1:
            names = ", ".join(r.label for r in majority_group)
            agreements.append(f"{len(majority_group)} of {len(ok)} responding models lined up together ({names}).")

        disagreements = [
            f"{len(group)} model(s) diverged from the rest: {', '.join(r.label for r in group)}."
            for label, group in groups.items() if label != majority_label
        ]

        primary = majority_group[0]
        final_answer = (
            f"Combined from {len(ok)} model response(s), leaning on {primary.label}'s answer as representative:\n\n"
            f"{primary.text}"
        )

        uncertainty_note = None
        if len(groups) > 1:
            uncertainty_note = "The panel did not fully agree - see disagreements below."
        if failed:
            note = f"{len(failed)} model(s) did not respond successfully: {', '.join(r.label for r in failed)}."
            uncertainty_note = f"{uncertainty_note} {note}" if uncertainty_note else note

        return CoordinatorResult(
            final_answer=final_answer,
            uncertainty_note=uncertainty_note,
            analysis=Analysis(agreements=agreements, disagreements=disagreements),
            supported_by={label: [r.model_id for r in group] for label, group in groups.items()},
        )


def build_coordinator(config: ModelConfig) -> CoordinatorAdapter:
    if config.provider == "mock":
        return MockCoordinatorAdapter(config)
    raise ValueError(f"Unknown coordinator provider '{config.provider}' for coordinator '{config.id}'")
