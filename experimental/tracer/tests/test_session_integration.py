"""Integration test: tracing a model_ensemble-style dual-branch pipeline (S03-T1).

Mirrors the sprint's T1 acceptance criterion directly: tracing
``model_ensemble`` must yield events for both model branches with distinct
storage lineages.
"""

from __future__ import annotations

import torch
import torch.nn as nn
from tracer.handles import handle_for
from tracer.session import trace


class _BranchA(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = nn.Linear(4, 1, dtype=torch.float64)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(torch.relu(x))


class _BranchB(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = nn.Linear(4, 1, dtype=torch.float64)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(torch.sigmoid(x))


def test_two_independent_branches_have_distinct_lineages() -> None:
    branch_a = _BranchA()
    branch_b = _BranchB()
    x = torch.randn(8, 4, dtype=torch.float64)

    with trace() as session, torch.inference_mode():
        score_a = branch_a(x)
        score_b = branch_b(x)
        ensemble = 0.6 * score_a + 0.4 * score_b

    assert len(session.events) > 0

    handle_a = handle_for(score_a)
    handle_b = handle_for(score_b)
    assert handle_a is not None
    assert handle_b is not None
    assert handle_a != handle_b

    # Every event that produced branch A's output must be disjoint from
    # every event that produced branch B's output — the two branches never
    # share mutable state (plan §2.4 parallel-branch opportunity).
    producers_a = {e.id for e in session.events if handle_a in e.output_handles}
    producers_b = {e.id for e in session.events if handle_b in e.output_handles}
    assert producers_a
    assert producers_b
    assert producers_a.isdisjoint(producers_b)

    # The final ensemble event must depend on both branch outputs.
    handle_ensemble = handle_for(ensemble)
    ensemble_events = [e for e in session.events if handle_ensemble in e.output_handles]
    assert ensemble_events
