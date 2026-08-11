"""Tests for the §33.2 machine metadata collector (cobra-bench doctor)."""

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from cobra_bench.doctor import (
    EnvironmentReport,
    collect_cpu_info,
    collect_gpu_info,
    collect_host_info,
    collect_software_info,
    run_doctor,
    validate_strict,
)

# ---------------------------------------------------------------------------
# Host info collector tests
# ---------------------------------------------------------------------------


class TestCollectHostInfo:
    def test_returns_hostname_alias(self) -> None:
        info = collect_host_info()
        assert isinstance(info["hostname_alias"], str)
        assert len(info["hostname_alias"]) > 0

    def test_returns_os(self) -> None:
        info = collect_host_info()
        assert isinstance(info["os"], str)
        assert len(info["os"]) > 0

    def test_returns_kernel(self) -> None:
        info = collect_host_info()
        assert isinstance(info["kernel"], str)
        assert len(info["kernel"]) > 0

    def test_returns_cpu(self) -> None:
        info = collect_host_info()
        assert isinstance(info["cpu"], str)
        assert len(info["cpu"]) > 0

    def test_returns_numa_nodes_as_int(self) -> None:
        info = collect_host_info()
        assert isinstance(info["numa_nodes"], int)
        assert info["numa_nodes"] >= 1

    def test_returns_memory_gb_as_float(self) -> None:
        info = collect_host_info()
        assert isinstance(info["memory_gb"], float)
        assert info["memory_gb"] > 0

    def test_manual_is_false(self) -> None:
        """Auto-collected host info must NOT be marked manual."""
        info = collect_host_info()
        assert info["manual"] is False


# ---------------------------------------------------------------------------
# CPU info collector tests
# ---------------------------------------------------------------------------


class TestCollectCpuInfo:
    def test_returns_cpu_model_string(self) -> None:
        info = collect_cpu_info()
        assert isinstance(info, str)
        assert len(info) > 0


# ---------------------------------------------------------------------------
# GPU info collector tests (all faked — CI has no GPU)
# ---------------------------------------------------------------------------


class TestCollectGpuInfo:
    def test_absent_when_nvidia_smi_not_found(self) -> None:
        """On a machine without nvidia-smi, gpu should report absent."""
        with patch(
            "cobra_bench.doctor.subprocess.run",
            side_effect=FileNotFoundError("nvidia-smi not found"),
        ):
            info = collect_gpu_info()
        assert info["status"] == "absent"
        assert info["gpu_name"] is None
        assert info["driver"] is None

    def test_absent_when_nvidia_smi_fails(self) -> None:
        """nvidia-smi present but fails (e.g. no driver loaded)."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("cobra_bench.doctor.subprocess.run", return_value=mock_result):
            info = collect_gpu_info()
        assert info["status"] == "absent"

    def test_present_with_full_nvidia_smi_output(self) -> None:
        """Fake a successful nvidia-smi --query-gpu response."""
        fake_csv = (
            "NVIDIA A100-SXM4-80GB, 535.129.03, 8.0, "
            "GPU-12345678-abcd-efgh-ijkl-123456789012, "
            "locked, 400.00, Enabled, Disabled\n"
        )
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_csv
        with patch("cobra_bench.doctor.subprocess.run", return_value=mock_result):
            info = collect_gpu_info()
        assert info["status"] == "present"
        assert info["gpu_name"] == "NVIDIA A100-SXM4-80GB"
        assert info["driver"] == "535.129.03"
        assert info["compute_capability"] == "8.0"
        assert info["clocks_policy"] == "locked"
        assert info["power_limit_watts"] == 400.0
        assert info["persistence_mode"] is True
        assert info["mig"] == "Disabled"
        assert info["gpu_uuid_hash"] is not None

    def test_manual_is_false(self) -> None:
        """GPU info collected via nvidia-smi must not be marked manual."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("cobra_bench.doctor.subprocess.run", return_value=mock_result):
            info = collect_gpu_info()
        assert info["manual"] is False

    def test_partial_nvidia_smi_output(self) -> None:
        """If nvidia-smi returns fewer fields than expected, handle gracefully."""
        fake_csv = "NVIDIA RTX 4090, 545.23.08\n"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_csv
        with patch("cobra_bench.doctor.subprocess.run", return_value=mock_result):
            info = collect_gpu_info()
        # Should still report present but missing fields are None
        assert info["status"] == "present"
        assert info["gpu_name"] == "NVIDIA RTX 4090"
        assert info["driver"] == "545.23.08"


# ---------------------------------------------------------------------------
# Software version collector tests
# ---------------------------------------------------------------------------


class TestCollectSoftwareInfo:
    def test_python_version_present(self) -> None:
        info = collect_software_info()
        assert isinstance(info["python"], str)
        assert info["python"] == platform.python_version()

    def test_missing_package_returns_none(self) -> None:
        """Packages not installed should have None values, not raise."""
        info = collect_software_info()
        # At minimum, python is present; others might be None on CI
        assert "python" in info

    def test_manual_is_false(self) -> None:
        info = collect_software_info()
        assert info["manual"] is False

    def test_detects_installed_packages(self) -> None:
        """If a tracked package is installed, its version is a string."""
        info = collect_software_info()
        for key in ("pytorch", "triton", "pandas", "cudf", "numpy", "pyarrow"):
            assert key in info
            assert info[key] is None or isinstance(info[key], str)

    def test_reports_versioned_cudf_distribution(self) -> None:
        info = collect_software_info()
        if info["cudf"] is not None:
            assert info["cudf"] == "26.6.0"


# ---------------------------------------------------------------------------
# Strict mode validation
# ---------------------------------------------------------------------------


class TestValidateStrict:
    def test_passes_when_all_fields_present(self) -> None:
        """A complete report with GPU present passes strict mode."""
        report = _make_full_report(gpu_status="present")
        errors = validate_strict(report)
        assert errors == []

    def test_fails_when_gpu_absent(self) -> None:
        """Strict mode requires GPU info when possible (§33.2)."""
        report = _make_full_report(gpu_status="absent")
        errors = validate_strict(report)
        assert any("gpu" in e.lower() for e in errors)

    def test_fails_when_host_fields_missing(self) -> None:
        report = _make_full_report(gpu_status="present")
        report["host"]["os"] = None
        errors = validate_strict(report)
        assert any("os" in e for e in errors)

    def test_fails_when_python_missing(self) -> None:
        report = _make_full_report(gpu_status="present")
        report["software"]["python"] = None
        errors = validate_strict(report)
        assert any("python" in e for e in errors)


# ---------------------------------------------------------------------------
# Full doctor run (integration)
# ---------------------------------------------------------------------------


class TestRunDoctor:
    def test_returns_environment_report(self) -> None:
        report = run_doctor(strict=False)
        assert isinstance(report, EnvironmentReport)
        assert "host" in report.data
        assert "gpu" in report.data
        assert "software" in report.data

    def test_writes_json_to_output_path(self, tmp_path: Path) -> None:
        out = tmp_path / "environment.json"
        report = run_doctor(strict=False, output=out)
        assert out.is_file()
        loaded = json.loads(out.read_text())
        assert loaded["host"]["hostname_alias"] == report.data["host"]["hostname_alias"]

    def test_strict_mode_returns_errors_on_gpu_absent(self) -> None:
        """On CI (no GPU), strict mode should fail with GPU-related errors."""
        with patch(
            "cobra_bench.doctor.subprocess.run",
            side_effect=FileNotFoundError("nvidia-smi not found"),
        ):
            report = run_doctor(strict=True)
            assert len(report.errors) > 0
            assert any("gpu" in e.lower() for e in report.errors)

    def test_strict_mode_exit_code_nonzero(self) -> None:
        """Strict mode should indicate failure when required fields missing."""
        with patch(
            "cobra_bench.doctor.subprocess.run",
            side_effect=FileNotFoundError("nvidia-smi not found"),
        ):
            report = run_doctor(strict=True)
            assert report.exit_code != 0

    def test_non_strict_mode_exit_code_zero(self) -> None:
        report = run_doctor(strict=False)
        assert report.exit_code == 0

    def test_json_output_is_valid(self, tmp_path: Path) -> None:
        out = tmp_path / "environment.json"
        run_doctor(strict=False, output=out)
        data = json.loads(out.read_text())
        # Must contain the three top-level sections
        assert "host" in data
        assert "gpu" in data
        assert "software" in data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_full_report(*, gpu_status: str = "present") -> dict[str, Any]:
    """Build a syntactically complete environment report dict."""
    report: dict[str, Any] = {
        "host": {
            "hostname_alias": "test-host",
            "os": "Linux",
            "kernel": "6.1.0",
            "cpu": "AMD EPYC 7763",
            "numa_nodes": 2,
            "memory_gb": 256.0,
            "manual": False,
        },
        "gpu": {
            "status": gpu_status,
            "gpu_name": "NVIDIA A100" if gpu_status == "present" else None,
            "driver": "535.129.03" if gpu_status == "present" else None,
            "compute_capability": "8.0" if gpu_status == "present" else None,
            "gpu_uuid_hash": "abc123" if gpu_status == "present" else None,
            "clocks_policy": "locked" if gpu_status == "present" else None,
            "power_limit_watts": 400.0 if gpu_status == "present" else None,
            "persistence_mode": True if gpu_status == "present" else None,
            "mig": "Disabled" if gpu_status == "present" else None,
            "manual": False,
        },
        "software": {
            "python": "3.13.0",
            "pytorch": None,
            "triton": None,
            "pandas": None,
            "cudf": None,
            "numpy": None,
            "pyarrow": None,
            "manual": False,
        },
    }
    return report
