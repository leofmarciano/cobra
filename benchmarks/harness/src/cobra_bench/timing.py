"""Timing protocol engine (plan §20.5, §33.5, §33.6).

Implements:

- Warmup-until-stable policy: min count, median band, max cap (reported as
  ``WarmupFailure`` when reached).
- ≥30 samples default.
- Randomized variant order to reduce thermal/temporal bias.
- Cold mode = process-per-sample (``ColdRunner``).
- Per-sample correctness hook: a failed oracle invalidates the variant's
  timings (raises ``CorrectnessFailed``, per §33.4).
- CUDA sync points as pluggable callables so the engine stays
  framework-agnostic.
"""

from __future__ import annotations

import random
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class WarmupFailure(RuntimeError):
    """Raised when warmup never stabilizes within the max warmup cap."""


class CorrectnessFailed(RuntimeError):
    """Raised when a per-sample correctness oracle returns False (§33.4)."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SampleResult:
    """One timing sample."""

    elapsed_s: float
    return_value: Any
    valid: bool
    warmup: bool


@dataclass
class TimingConfig:
    """Configuration for the timing protocol engine."""

    warmup_policy: str = "stability"
    minimum_samples: int = 30
    max_warmup: int = 100
    stability_band: float = 0.05
    stability_window: int = 5
    randomize_order: bool = True
    correctness_required: bool = True


# ---------------------------------------------------------------------------
# Timing engine (warm-path)
# ---------------------------------------------------------------------------

# Type alias for the optional sync callables
SyncCallable = Callable[[], None]


def _noop() -> None:
    """Default no-op sync callable."""


@dataclass
class TimingEngine:
    """Core timing engine for warm-path measurement (§33.6).

    Parameters
    ----------
    config:
        Timing protocol configuration.
    clock:
        Callable returning monotonic time in seconds.  Defaults to
        ``time.perf_counter``.  Pass a fake for deterministic tests.
    pre_sync:
        Called before each sample timing starts (e.g. CUDA sync).
    post_sync:
        Called after each sample timing ends (e.g. CUDA sync).
    """

    config: TimingConfig = field(default_factory=TimingConfig)
    clock: Callable[[], float] = field(default=time.perf_counter)
    pre_sync: SyncCallable = field(default=_noop)
    post_sync: SyncCallable = field(default=_noop)

    # ----- public API -----

    def run_warm(
        self,
        workload: Callable[[], Any],
        *,
        oracle: Callable[[Any], bool] | None = None,
    ) -> list[SampleResult]:
        """Run the warm-path timing protocol.

        Raises
        ------
        ValueError
            If ``correctness_required`` and no oracle is provided.
        WarmupFailure
            If warmup does not stabilize within ``max_warmup`` samples.
        CorrectnessFailed
            If a per-sample oracle check returns ``False``.
        """
        cfg = self.config

        if cfg.correctness_required and oracle is None:
            msg = (
                "correctness_required is True but no oracle was provided; "
                "pass oracle=... or set correctness_required=False "
                "(use --no-oracle with a loud warning)"
            )
            raise ValueError(msg)

        # Phase 1: warmup
        self._run_warmup(workload, oracle)

        # Phase 2: measurement samples
        results: list[SampleResult] = []
        for _ in range(cfg.minimum_samples):
            sample = self._take_sample(workload, oracle, warmup=False)
            results.append(sample)

        return results

    def randomize_variants(self, variants: list[T], *, seed: int | None = None) -> list[T]:
        """Return a (possibly shuffled) copy of the variant list."""
        ordered = list(variants)
        if self.config.randomize_order:
            rng = random.Random(seed)
            rng.shuffle(ordered)
        return ordered

    # ----- internal -----

    def _take_sample(
        self,
        workload: Callable[[], Any],
        oracle: Callable[[Any], bool] | None,
        *,
        warmup: bool,
    ) -> SampleResult:
        """Time a single workload invocation, with sync and oracle."""
        self.pre_sync()
        t0 = self.clock()
        result = workload()
        t1 = self.clock()
        self.post_sync()

        elapsed = t1 - t0
        valid = True

        if oracle is not None and not oracle(result):
            raise CorrectnessFailed(f"Correctness oracle failed for sample (result={result!r})")

        return SampleResult(
            elapsed_s=elapsed,
            return_value=result,
            valid=valid,
            warmup=warmup,
        )

    def _run_warmup(
        self,
        workload: Callable[[], Any],
        oracle: Callable[[Any], bool] | None,
    ) -> list[float]:
        """Run warmup samples until stability is reached or max_warmup exceeded."""
        cfg = self.config
        times: list[float] = []

        for _ in range(cfg.max_warmup):
            sample = self._take_sample(workload, oracle, warmup=True)
            times.append(sample.elapsed_s)

            if len(times) >= cfg.stability_window and self._is_stable(times):
                return times

        raise WarmupFailure(
            f"Warmup did not stabilize after {cfg.max_warmup} samples "
            f"(policy={cfg.warmup_policy}, band={cfg.stability_band}, "
            f"window={cfg.stability_window})"
        )

    def _is_stable(self, times: list[float]) -> bool:
        """Check if the last ``stability_window`` samples are within the band."""
        cfg = self.config
        window = times[-cfg.stability_window :]
        if len(window) < cfg.stability_window:
            return False

        med = statistics.median(window)
        if med == 0:
            # All zeros is stable
            return all(t == 0 for t in window)

        # All samples within band of the median
        return all(abs(t - med) / med <= cfg.stability_band for t in window)


# ---------------------------------------------------------------------------
# Cold-path runner (process-per-sample, §33.5)
# ---------------------------------------------------------------------------


@dataclass
class ColdRunner:
    """Cold-path runner: each sample is executed in a fresh subprocess.

    This is a structural placeholder for S01; the full subprocess protocol
    is wired in T5 (CLI assembly).
    """

    config: TimingConfig = field(default_factory=TimingConfig)
