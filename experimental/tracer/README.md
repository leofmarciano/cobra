DISPOSABLE — not release code (plan §18.4).

# tracer

A throwaway whole-program tracer spike for Project Cobra (S03,
`orchestration/sprints/S03-disposable-tracer.md`; plan §29 Days 11-20). Its
sole purpose is to prove that Cobra can *observe* a real cross-library
pipeline — call boundaries, tensor/dataframe metadata, dependencies, and
timings — before any compiler exists. It de-risks the whole-program capture
thesis (plan §6.1-6.2).

This code:

- lives under `experimental/`, is excluded from release packaging, and is
  never imported by `python/cobra_compiler`.
- will be deleted or entirely rewritten once S10 lowers real captures into
  Cobra IR. Do not build production features on top of it.
- intentionally trades completeness for simplicity: unknown calls become
  opaque nodes (plan §6.2/§6.3) rather than failing.

## What it records

Four recorders, one per plan §6.2 capture level relevant to v0.1's target
libraries:

- **torch** (`tracer.torch_mode.TracingTorchFunctionMode`) — every
  `torch.*` call, intercepted via `torch.overrides.TorchFunctionMode`
  (plan §6.2 "tensor graph" level).
- **pandas** (`tracer.pandas_wrap.pandas_recorder`) — the plan §10.1
  v0.1-supported operation subset, via method wrapping on
  `DataFrame`/`Series` plus `pandas.read_parquet`. Anything outside that
  list runs unrecorded, matching §10.1's "unsupported operations
  materialize and fall back" rule.
- **numpy** (`tracer.numpy_wrap`) — real `__array_function__` dispatch on
  `TracedArray`-wrapped ndarrays (`tracer.numpy_wrap.wrap`); tracing
  propagates through chains of numpy calls because results are re-wrapped.
- **opaque** (`tracer.opaque`) — explicit wrapper (`opaque()` decorator or
  `call_opaque()`) for anything else. Opaque nodes get conservative
  ordering edges to their neighbors in the DAG builder (S03-T2), never
  assumed independence (plan §6.3 spirit).

Each recorded `Event` (`tracer.events.Event`) captures: op name, an
args/kwargs summary, value-identity handles for inputs/outputs
(`tracer.handles`, keyed by tensor storage pointer / dataframe object id /
ndarray base id — so views of the same storage share a handle), per-value
metadata (dtype, shape/schema, device, storage id —
`tracer.metadata.describe`), wall-clock timing (`time.perf_counter_ns`),
thread id, and a best-effort call-site source location.

## Usage

```python
from tracer import trace

with trace() as session:
    result = my_pipeline(x)

for event in session.events:
    print(event.op, event.duration_ns, event.input_handles, event.output_handles)
```

## Building a DAG

```python
from tracer import build_dag, to_json, to_dot
from tracer.session import trace

with trace() as session:
    result = my_pipeline(x)

dag = build_dag(session.events)
print(to_json(dag))
print(to_dot(dag))
```

## Critical-path / parallelism analysis (S03-T3)

```python
from tracer import analyze

metrics = analyze(dag)
print(metrics["critical_path_ns"], metrics["max_speedup"])
print(metrics["top5_critical_ops"])
print(metrics["transfer_boundaries"])
print(metrics["parallel_regions"])
```

Analysis returns:

* `total_work_ns` — sum of recorded op durations.
* `critical_path_ns` — longest dependency-path duration (span).
* `max_speedup` — work / span.
* `top5_critical_ops` — five largest contributors on the critical path.
* `transfer_boundaries` — explicit host/device `.to`/`.cpu`/`.cuda`/`from_numpy` events.
* `device_timeline` — coarse CPU/GPU phase transition points.
* `parallel_regions` — fork/join subgraphs where independent branches could overlap.

## Generating workload reports

```bash
uv run python -m tracer.run --workload all --out experimental/tracer/reports/
```

This traces the three Phase 0 workloads, writes a Markdown report and a
Graphviz DOT file per workload, and produces the findings memo at
`docs/benchmarks/phase0-tracer-findings.md`.

## JSON schema (S10 handoff note)

`tracer.dag` (S03-T2) exports the recorded events plus dependency edges as
JSON. Keep that schema documented here as it evolves — S10 converts it into
real Cobra IR, so it is the one artifact from this spike expected to
outlive `experimental/`.

```json
{
  "nodes": [
    {
      "id": 0,
      "kind": "torch",
      "op": "torch.relu",
      "args_summary": "Tensor(...)",
      "metadata": {...},
      "duration_ns": 1234,
      "thread_id": 1234567890,
      "source": "pipeline.py:42"
    }
  ],
  "edges": [
    {"from": 0, "to": 1, "kind": "data"},
    {"from": 1, "to": 2, "kind": "order"}
  ],
  "roots": [0],
  "leaves": [2]
}
```

Edge kinds:

* `data` — the consumer reads a handle last produced by the source event.
* `order` — either the source and target mutate the same storage identity, or
  an unknown-effect `opaque` node is being fenced against its program-order
  neighbors (plan §6.3 spirit).
