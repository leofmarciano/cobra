"""Tests for the §33.10 result schema and JSON-lines/Parquet IO."""

from __future__ import annotations

from pathlib import Path

from cobra_bench.results import (
    SampleRecord,
    dict_to_record,
    read_jsonl,
    read_parquet,
    record_to_dict,
    write_jsonl,
    write_parquet,
)


def _make_sample(variant: str = "a", sample: int = 0, **overrides: object) -> SampleRecord:
    defaults = {
        "run_id": "r1",
        "workload": "dummy_add",
        "variant": variant,
        "phase": "warm",
        "sample": sample,
        "correct": True,
        "wall_time_ns": 1_000_000,
        "gpu_time_ns": None,
        "cpu_time_ns": 500_000,
        "peak_host_bytes": 0,
        "peak_device_bytes": None,
        "h2d_bytes": 0,
        "d2h_bytes": 0,
        "kernel_launches": 0,
        "graph_breaks": 0,
        "fallback_nodes": 0,
        "compile_time_ns": None,
        "cache_hit": None,
        "guard_failures": None,
        "gpu_temperature_c": None,
        "throttled": False,
    }
    defaults.update(overrides)
    return SampleRecord(**defaults)


class TestRecordSerialization:
    def test_round_trip_via_dict(self) -> None:
        record = _make_sample()
        d = record_to_dict(record)
        restored = dict_to_record(d)
        assert restored == record

    def test_zero_is_preserved_not_converted_to_none(self) -> None:
        """Real zero values must survive serialization; only ``None`` means absent."""
        record = _make_sample(
            wall_time_ns=0,
            peak_host_bytes=0,
            kernel_launches=0,
            throttled=False,
        )
        d = record_to_dict(record)
        assert d["wall_time_ns"] == 0
        assert d["peak_host_bytes"] == 0
        assert d["kernel_launches"] == 0
        assert d["throttled"] is False
        assert d["gpu_time_ns"] is None

    def test_unknown_fields_ignored_on_load(self) -> None:
        d = record_to_dict(_make_sample())
        d["future_metric"] = 123
        restored = dict_to_record(d)
        assert not hasattr(restored, "future_metric")


class TestJsonlIO:
    def test_write_and_read_jsonl(self, tmp_path: Path) -> None:
        path = tmp_path / "samples.jsonl"
        records = [_make_sample(variant="a", sample=i) for i in range(3)]
        write_jsonl(records, path)
        restored = read_jsonl(path)
        assert restored == records

    def test_jsonl_preserves_nulls(self, tmp_path: Path) -> None:
        path = tmp_path / "samples.jsonl"
        record = _make_sample(gpu_time_ns=None, peak_device_bytes=None)
        write_jsonl([record], path)
        restored = read_jsonl(path)[0]
        assert restored.gpu_time_ns is None
        assert restored.peak_device_bytes is None
        assert restored.peak_host_bytes == 0


class TestParquetIO:
    def test_write_and_read_parquet(self, tmp_path: Path) -> None:
        path = tmp_path / "samples.parquet"
        records = [_make_sample(variant="a", sample=i) for i in range(5)]
        write_parquet(records, path)
        restored = read_parquet(path)
        assert restored == records

    def test_parquet_preserves_nulls(self, tmp_path: Path) -> None:
        path = tmp_path / "samples.parquet"
        record = _make_sample(
            gpu_time_ns=None,
            compile_time_ns=None,
            cache_hit=None,
        )
        write_parquet([record], path)
        restored = read_parquet(path)[0]
        assert restored.gpu_time_ns is None
        assert restored.compile_time_ns is None
        assert restored.cache_hit is None
        assert restored.wall_time_ns == 1_000_000

    def test_parquet_preserves_zero_values(self, tmp_path: Path) -> None:
        path = tmp_path / "samples.parquet"
        record = _make_sample(
            wall_time_ns=0,
            h2d_bytes=0,
            kernel_launches=0,
            throttled=False,
        )
        write_parquet([record], path)
        restored = read_parquet(path)[0]
        assert restored.wall_time_ns == 0
        assert restored.h2d_bytes == 0
        assert restored.kernel_launches == 0
        assert restored.throttled is False

    def test_parquet_round_trip_multiple_variants(self, tmp_path: Path) -> None:
        path = tmp_path / "samples.parquet"
        records = [
            _make_sample(variant="a", sample=i, wall_time_ns=100_000 * (i + 1)) for i in range(3)
        ] + [_make_sample(variant="b", sample=i, wall_time_ns=50_000 * (i + 1)) for i in range(3)]
        write_parquet(records, path)
        restored = read_parquet(path)
        assert restored == records
