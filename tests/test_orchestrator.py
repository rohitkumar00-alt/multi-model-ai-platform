import asyncio
import time

from app.adapters.base import Generation, ModelAdapter, ModelCallError
from app.config import ModelConfig
from app.orchestrator import fan_out
from app.schemas import ModelStatus


class FakeAdapter(ModelAdapter):
    def __init__(self, model_id, delay=0.0, fail=False, crash=False):
        super().__init__(ModelConfig(
            id=model_id, label=model_id, provider="fake",
            price_per_1k_input_usd=1.0, price_per_1k_output_usd=2.0,
        ))
        self.delay, self.fail, self.crash = delay, fail, crash

    async def generate(self, prompt):
        await asyncio.sleep(self.delay)
        if self.fail:
            raise ModelCallError("boom")
        if self.crash:
            raise KeyError("internal detail that must not leak")
        return Generation(text=f"answer from {self.config.id}", tokens_in=1000, tokens_out=500)


def run(adapters, timeout=5.0):
    return asyncio.run(fan_out("hi", adapters, timeout))


def test_models_run_in_parallel():
    start = time.perf_counter()
    results = run([FakeAdapter("a", delay=0.5), FakeAdapter("b", delay=0.5), FakeAdapter("c", delay=0.5)])
    assert time.perf_counter() - start < 1.0  # sequential would take 1.5s
    assert all(r.status == ModelStatus.OK for r in results)


def test_results_keep_input_order_and_identity():
    results = run([FakeAdapter("slow", delay=0.3), FakeAdapter("fast", delay=0.0)])
    assert [r.model_id for r in results] == ["slow", "fast"]
    assert results[0].text == "answer from slow"


def test_timeout_does_not_block_others():
    results = run([FakeAdapter("ok"), FakeAdapter("hang", delay=3)], timeout=0.5)
    assert results[0].status == ModelStatus.OK
    assert results[1].status == ModelStatus.TIMEOUT


def test_expected_error_is_reported():
    r = run([FakeAdapter("bad", fail=True)])[0]
    assert r.status == ModelStatus.ERROR and r.error_message == "boom"


def test_unexpected_error_does_not_leak_details():
    r = run([FakeAdapter("crash", crash=True)])[0]
    assert r.status == ModelStatus.ERROR
    assert "internal detail" not in r.error_message


def test_cost_estimate():
    r = run([FakeAdapter("a")])[0]
    assert r.est_cost_usd == 2.0  # 1k in * $1 + 0.5k out * $2
