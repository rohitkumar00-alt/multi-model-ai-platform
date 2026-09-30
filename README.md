# Multi-Model Answer Platform - Milestones 1-3

Ask one question, send it to several (mock) models in parallel, and get:
- every model's individual answer, with status/latency/cost
- a coordinator's combined answer, with agreement/disagreement notes and an
  uncertainty note when the panel didn't fully agree or some models failed

Everything runs on your machine. No API keys needed yet - every model is a
mock (see models.yaml). Real providers are a later, separate step, and you
choose which one before any paid service is wired in.

## Run it

    python -m venv .venv
    # Windows:        .venv\Scripts\activate
    # macOS/Linux:     source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Then open **http://127.0.0.1:8000/** for the actual app (a page, checkboxes,
an "Ask all models" button). http://127.0.0.1:8000/docs is still there too,
for calling the API directly.

## What's new since Milestone 1
- `app/coordinator.py` - the coordinator step. In this build it's rule-based
  (no real "understanding" of the answers) so the whole flow works with zero
  setup; a real, meaning-aware coordinator can be dropped in later behind the
  same `CoordinatorAdapter` interface, the same way model adapters are.
- `static/index.html` - the frontend, served by FastAPI itself. It calls
  `/api/models` and `/api/ask` with real `fetch()` requests; no simulated
  logic lives in the browser anymore.
- `/api/ask` now returns a `coordinator` field alongside the per-model
  `results`, so the UI (or any client) can show both.

## Try it without the browser

    curl -X POST http://127.0.0.1:8000/api/ask \
      -H "Content-Type: application/json" \
      -d '{"question":"What is Python?","model_ids":["mock-fast","mock-thoughtful","mock-flaky","mock-slow"],"timeout_seconds":2}'

You'll see two models succeed, one simulated error, one timeout, and a
`coordinator` block that combines the successes and calls out the failures.

## A note on the mock coordinator
It groups models by a fixed per-model label (see `app/stance.py`) - it does
not actually read or compare meaning. This is intentional: it lets you see
and test the full shape of a real synthesis (agreements, disagreements, an
uncertainty note, a combined answer) before spending anything on a real
model. Whatever coordinator is used, mock or real, treat its output as a
helpful synthesis, not a guaranteed-correct answer - it can misjudge
agreement, share the panel's blind spots, or make its own mistakes.

## Tests

    python -m pytest -q

16 tests cover parallel execution, timeouts, error handling, input
validation, and the coordinator's behavior with 0, 1, and multiple
successful responses.

## What's next (not built yet)
- A real provider adapter (you choose: local via Ollama, OpenRouter, or a
  direct provider key) behind the same `ModelAdapter` interface.
- Optionally, a real LLM-backed coordinator once at least one real model is
  wired in.
- Request history/storage, if you want it - v1 keeps no state.
