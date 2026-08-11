"""Result schema and sample storage (plan §33.10).

The schema distinguishes a real zero from an unavailable metric by using
``None`` for the latter.  Samples are persisted as JSON-lines and as
Parquet (via pyarrow) so downstream tooling can consume them efficiently.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]


@dataclass
class SampleRecord:
    """One measured sample, per plan §33.10.

    Numeric fields are ``int | None`` so that ``0`` means "the measured
    value was zero" while ``None`` means "this metric was not available".
    """

    run_id: str
    workload: str
    variant: str
    phase: str
    sample: int
    correct: bool
    wall_time_ns: int | None = None
    gpu_time_ns: int | None = None
    cpu_time_ns: int | None = None
    peak_host_bytes: int | None = None
    peak_device_bytes: int | None = None
    h2d_bytes: int | None = None
    d2h_bytes: int | None = None
    kernel_launches: int | None = None
    graph_breaks: int | None = None
    fallback_nodes: int | None = None
    compile_time_ns: int | None = None
    cache_hit: bool | None = None
    guard_failures: int | None = None
    gpu_temperature_c: int | None = None
    throttled: bool | None = None
    tags: dict[str, str] = field(default_factory=dict)


def record_to_dict(record: SampleRecord) -> dict[str, Any]:
    """Serialize a record to a plain dict suitable for JSON/Parquet."""
    return asdict(record)


def dict_to_record(data: dict[str, Any]) -> SampleRecord:
    """Deserialize a dict back to a ``SampleRecord``.

    Unknown keys are ignored so the schema can evolve without breaking
    readers.
    """
    valid_fields = {f.name for f in fields(SampleRecord)}
    kwargs = {k: v for k, v in data.items() if k in valid_fields}
    return SampleRecord(**kwargs)


# ---------------------------------------------------------------------------
# JSON-lines
# ---------------------------------------------------------------------------


def write_jsonl(records: list[SampleRecord], path: str | Path) -> None:
    """Write records as newline-delimited JSON."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record_to_dict(record), sort_keys=True) + "\n")


def read_jsonl(path: str | Path) -> list[SampleRecord]:
    """Read records from a JSON-lines file."""
    records: list[SampleRecord] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(dict_to_record(json.loads(line)))
    return records


# ---------------------------------------------------------------------------
# Parquet
# ---------------------------------------------------------------------------

_PARQUET_SCHEMA = pa.schema(
    [
        ("run_id", pa.string()),
        ("workload", pa.string()),
        ("variant", pa.string()),
        ("phase", pa.string()),
        ("sample", pa.int64()),
        ("correct", pa.bool_()),
        ("wall_time_ns", pa.int64()),
        ("gpu_time_ns", pa.int64()),
        ("cpu_time_ns", pa.int64()),
        ("peak_host_bytes", pa.int64()),
        ("peak_device_bytes", pa.int64()),
        ("h2d_bytes", pa.int64()),
        ("d2h_bytes", pa.int64()),
        ("kernel_launches", pa.int64()),
        ("graph_breaks", pa.int64()),
        ("fallback_nodes", pa.int64()),
        ("compile_time_ns", pa.int64()),
        ("cache_hit", pa.bool_()),
        ("guard_failures", pa.int64()),
        ("gpu_temperature_c", pa.int64()),
        ("throttled", pa.bool_()),
    ]
)


def _records_to_table(records: list[SampleRecord]) -> pa.Table:
    """Build a pyarrow Table from sample records, mapping None to null."""
    data: dict[str, list[Any]] = {name: [] for name in _PARQUET_SCHEMA.names}
    for record in records:
        d = record_to_dict(record)
        for name in _PARQUET_SCHEMA.names:
            data[name].append(d.get(name))
    return pa.table(data, schema=_PARQUET_SCHEMA)


def write_parquet(records: list[SampleRecord], path: str | Path) -> None:
    """Write records to a Parquet file, creating parent dirs as needed."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(_records_to_table(records), out)


def read_parquet(path: str | Path) -> list[SampleRecord]:
    """Read records from a Parquet file."""
    table = pq.read_table(Path(path))
    records: list[SampleRecord] = []
    columns = {name: table.column(name).to_pylist() for name in table.column_names}
    n_rows = table.num_rows
    for i in range(n_rows):
        record_dict = {name: columns[name][i] for name in table.column_names}
        records.append(dict_to_record(record_dict))
    return records
