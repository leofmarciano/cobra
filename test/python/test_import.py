"""Smoke test that the cobra_compiler package is importable."""

import cobra_compiler as cobra


def test_version() -> None:
    assert cobra.__version__ == "0.0.1.dev0"
