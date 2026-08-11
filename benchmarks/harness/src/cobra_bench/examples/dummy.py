"""Two trivial, equivalent workload variants for `benchmarks/suites/example.yaml`.

They exist so the harness pipeline (manifest -> run -> analyze) can be
exercised end-to-end without depending on any Cobra internals or real
workloads (those arrive in S02).
"""


def variant_a() -> int:
    """Baseline: sum 0..999 with a Python loop."""
    total = 0
    for i in range(1000):
        total += i
    return total


def variant_b() -> int:
    """Optimized: the same sum computed with the closed-form formula."""
    n = 999
    return n * (n + 1) // 2
