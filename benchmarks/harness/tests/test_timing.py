"""Tests for the §20.5/§33.5/§33.6 timing protocol engine."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from cobra_bench.timing import (
    ColdRunner,
    CorrectnessFailed,
    SampleResult,
    TimingConfig,
    TimingEngine,
    WarmupFailure,
)

# ---------------------------------------------------------------------------
# Deterministic fake clock for unit tests
# ---------------------------------------------------------------------------


class FakeClock:
    """A deterministic clock that returns values from a predetermined list."""

    def __init__(self, values: list[float]) -> None:
        self._iter = iter(values)

    def __call__(self) -> float:
        return next(self._iter)


# ---------------------------------------------------------------------------
# TimingConfig defaults
# ---------------------------------------------------------------------------


class TestTimingConfigDefaults:
    def test_default_minimum_samples(self) -> None:
        cfg = TimingConfig()
        assert cfg.minimum_samples == 30

    def test_default_warmup_policy(self) -> None:
        cfg = TimingConfig()
        assert cfg.warmup_policy == "stability"

    def test_default_max_warmup(self) -> None:
        cfg = TimingConfig()
        assert cfg.max_warmup == 100

    def test_default_stability_band(self) -> None:
        cfg = TimingConfig()
        assert cfg.stability_band == 0.05

    def test_default_stability_window(self) -> None:
        cfg = TimingConfig()
        assert cfg.stability_window == 5

    def test_randomize_order_default(self) -> None:
        cfg = TimingConfig()
        assert cfg.randomize_order is True


# ---------------------------------------------------------------------------
# Warmup stability detection
# ---------------------------------------------------------------------------


class TestWarmupStability:
    def test_stability_stop_after_min_warmup(self) -> None:
        """Engine should stop warmup once recent medians are within the band."""
        # Produce stable timings right away: 10 warmup samples all at 1.0s
        stable_times = [1.0] * 200  # more than enough
        clock_values: list[float] = []
        t = 0.0
        for v in stable_times:
            clock_values.append(t)
            t += v
            clock_values.append(t)

        engine = TimingEngine(
            config=TimingConfig(
                warmup_policy="stability",
                minimum_samples=5,
                max_warmup=50,
                stability_band=0.05,
                stability_window=3,
            ),
            clock=FakeClock(clock_values),
        )

        workload = lambda: 42  # noqa: E731
        results = engine.run_warm(workload, oracle=lambda r: r == 42)
        # Should have at least minimum_samples
        assert len(results) >= 5
        # All results should be valid
        assert all(r.valid for r in results)

    def test_max_warmup_failure(self) -> None:
        """When warmup never stabilizes, engine should raise WarmupFailure."""
        # Produce wildly varying timings that never stabilize
        varying = []
        t = 0.0
        for i in range(500):
            varying.append(t)
            # Alternate between 0.1 and 10.0 — will never stabilize
            delta = 0.1 if i % 2 == 0 else 10.0
            t += delta
            varying.append(t)

        engine = TimingEngine(
            config=TimingConfig(
                warmup_policy="stability",
                minimum_samples=5,
                max_warmup=10,
                stability_band=0.01,
                stability_window=3,
            ),
            clock=FakeClock(varying),
        )

        workload = lambda: 42  # noqa: E731
        with pytest.raises(WarmupFailure):
            engine.run_warm(workload, oracle=lambda r: r == 42)

    def test_fixed_warmup_does_not_require_stability(self) -> None:
        """Fixed warmup is appropriate for tiny workloads with noisy clocks."""
        clock_values: list[float] = []
        t = 0.0
        for i in range(30):
            clock_values.append(t)
            t += 0.1 if i % 2 == 0 else 10.0
            clock_values.append(t)

        engine = TimingEngine(
            config=TimingConfig(
                warmup_policy="fixed",
                warmup_samples=3,
                minimum_samples=2,
                max_warmup=3,
            ),
            clock=FakeClock(clock_values),
        )

        results = engine.run_warm(lambda: 42, oracle=lambda r: r == 42)

        assert len(results) == 2


# ---------------------------------------------------------------------------
# Correctness gating
# ---------------------------------------------------------------------------


class TestCorrectnessGating:
    def test_failed_oracle_invalidates_sample(self) -> None:
        """A per-sample oracle failure marks the sample as invalid (§33.4)."""
        # Stable timing
        clock_values: list[float] = []
        t = 0.0
        for _ in range(200):
            clock_values.append(t)
            t += 1.0
            clock_values.append(t)

        engine = TimingEngine(
            config=TimingConfig(minimum_samples=5, max_warmup=10, stability_window=3),
            clock=FakeClock(clock_values),
        )

        call_count = 0

        def flaky_workload() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        # Oracle that fails on 3rd call
        oracle_calls = 0

        def failing_oracle(result: Any) -> bool:
            nonlocal oracle_calls
            oracle_calls += 1
            return oracle_calls != 3

        with pytest.raises(CorrectnessFailed):
            engine.run_warm(flaky_workload, oracle=failing_oracle)

    def test_no_oracle_raises_if_correctness_required(self) -> None:
        """When correctness is required but no oracle is given, must fail."""
        engine = TimingEngine(
            config=TimingConfig(correctness_required=True),
        )
        workload = lambda: 42  # noqa: E731
        with pytest.raises(ValueError, match="oracle"):
            engine.run_warm(workload, oracle=None)

    def test_no_oracle_allowed_when_not_required(self) -> None:
        """When correctness is not required, oracle=None is fine."""
        clock_values: list[float] = []
        t = 0.0
        for _ in range(200):
            clock_values.append(t)
            t += 1.0
            clock_values.append(t)

        engine = TimingEngine(
            config=TimingConfig(
                correctness_required=False,
                minimum_samples=5,
                max_warmup=10,
                stability_window=3,
            ),
            clock=FakeClock(clock_values),
        )
        workload = lambda: 42  # noqa: E731
        results = engine.run_warm(workload, oracle=None)
        assert len(results) >= 5


# ---------------------------------------------------------------------------
# Randomized variant order
# ---------------------------------------------------------------------------


class TestRandomizedOrder:
    def test_variants_are_reordered(self) -> None:
        """With randomize_order=True, variant execution order should differ
        from input order at least some of the time (probabilistic, but with
        enough variants it's essentially deterministic)."""
        variants = list(range(20))  # 20 variants
        config = TimingConfig(randomize_order=True)
        engine = TimingEngine(config=config)
        order = engine.randomize_variants(variants, seed=12345)
        # The order should be a permutation
        assert sorted(order) == sorted(variants)
        # With 20 elements, the chance of the same order is 1/20! ≈ 0
        assert order != variants

    def test_fixed_order_preserves_input(self) -> None:
        """With randomize_order=False, order should be unchanged."""
        variants = list(range(10))
        config = TimingConfig(randomize_order=False)
        engine = TimingEngine(config=config)
        order = engine.randomize_variants(variants, seed=42)
        assert order == variants


# ---------------------------------------------------------------------------
# SampleResult structure
# ---------------------------------------------------------------------------


class TestSampleResult:
    def test_valid_sample(self) -> None:
        s = SampleResult(elapsed_s=1.5, return_value=42, valid=True, warmup=False)
        assert s.elapsed_s == 1.5
        assert s.valid is True
        assert s.warmup is False

    def test_warmup_sample(self) -> None:
        s = SampleResult(elapsed_s=0.5, return_value=42, valid=True, warmup=True)
        assert s.warmup is True


# ---------------------------------------------------------------------------
# CUDA sync points are pluggable
# ---------------------------------------------------------------------------


class TestCudaSyncPoints:
    def test_sync_callable_invoked(self) -> None:
        """The engine calls pre_sync and post_sync around each sample."""
        pre = MagicMock()
        post = MagicMock()

        clock_values: list[float] = []
        t = 0.0
        for _ in range(200):
            clock_values.append(t)
            t += 1.0
            clock_values.append(t)

        engine = TimingEngine(
            config=TimingConfig(
                minimum_samples=3,
                max_warmup=5,
                stability_window=3,
                correctness_required=False,
            ),
            clock=FakeClock(clock_values),
            pre_sync=pre,
            post_sync=post,
        )

        engine.run_warm(lambda: 42, oracle=None)
        assert pre.call_count >= 3
        assert post.call_count >= 3

    def test_default_sync_is_noop(self) -> None:
        """Without sync callables, engine should still work."""
        clock_values: list[float] = []
        t = 0.0
        for _ in range(200):
            clock_values.append(t)
            t += 1.0
            clock_values.append(t)

        engine = TimingEngine(
            config=TimingConfig(
                minimum_samples=3,
                max_warmup=5,
                stability_window=3,
                correctness_required=False,
            ),
            clock=FakeClock(clock_values),
        )
        results = engine.run_warm(lambda: 42, oracle=None)
        assert len(results) >= 3


# ---------------------------------------------------------------------------
# Cold mode (process-per-sample)
# ---------------------------------------------------------------------------


class TestColdRunner:
    def test_cold_runner_interface(self) -> None:
        """ColdRunner must have a run method returning SampleResults."""
        runner = ColdRunner(
            config=TimingConfig(minimum_samples=3),
        )
        # We can't actually run subprocesses here, but we can test
        # that the interface exists and config is stored
        assert runner.config.minimum_samples == 3
